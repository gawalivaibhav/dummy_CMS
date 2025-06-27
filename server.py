import logging
import json
import datetime
import asyncio # Import asyncio for WebSocket client
import websockets # Import websockets for WebSocket client

# Import Quart specific modules
from quart import Quart, websocket, jsonify, request, Response

# Import database functions from database.py
from database import init_db, create_session, update_session, get_all_sessions

app = Quart(__name__)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the database when the app starts
@app.before_serving
async def initialize_database():
    """Initialize the database before the server starts serving requests."""
    logging.info("Initializing database...")
    init_db()
    logging.info("Database initialization complete.")

# --- WebSocket Client Function ---
async def send_ocpp_message(message: list):
    """Connects to the OCPP WebSocket server and sends a message."""
    uri = "ws://localhost:5050/ocpp"
    try:
        # Use connect as a context manager for automatic closing
        async with websockets.connect(uri) as websocket:
            logging.info(f"WebSocket client connecting to {uri} from HTTP handler.")
            await websocket.send(json.dumps(message))
            logging.info(f"WebSocket client sent message from HTTP handler: {message}")

            # Optional: Wait for a response if the server sends one immediately
            # Your WebSocket server handler on /ocpp will likely send a response (e.g., CallResult)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0) # Short timeout
                logging.info(f"WebSocket client received response from HTTP handler: {response}")
                return response
            except asyncio.TimeoutError:
                logging.warning("WebSocket client from HTTP handler timed out waiting for response.")
                return None
            except websockets.exceptions.ConnectionClosedOK:
                 logging.info("WebSocket server closed connection gracefully after message from HTTP handler.")
                 return None


    except ConnectionRefusedError:
        logging.error(f"WebSocket connection refused by server at {uri} from HTTP handler. Is the WebSocket server running?")
    except Exception as e:
        logging.error(f"WebSocket client from HTTP handler encountered an error: {e}", exc_info=True)
    return None # Return None on error


# --- HTTP Routes ---
@app.route('/start_charging', methods=['POST'])
async def start_charging_http():
    logging.info("Received HTTP request to /start_charging")
    request_data = await request.get_json() or {} # Get request body if JSON

    # Extract relevant data from the HTTP request body for the OCPP message
    # This is an example mapping; adjust based on your HTTP request structure
    id_tag = request_data.get("idTag", "UnknownIdTag")
    connector_id = request_data.get("connectorId", 1) # Default connectorId
    meter_start = request_data.get("meterStart", 0)
    timestamp = request_data.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z")


    # Prepare the OCPP StartTransaction.req message (OCPP 1.6J format)
    ocpp_message = [
        2, # MessageTypeId: Call
        str(datetime.datetime.now().timestamp()), # Generate a unique MessageId (timestamp is simple)
        "StartTransaction", # Action
        { # Payload
            "connectorId": connector_id,
            "idTag": id_tag,
            "meterStart": meter_start,
            "timestamp": timestamp # Use the provided timestamp or generated
        }
    ]

    logging.info(f"Attempting to send OCPP StartTransaction message via WebSocket client: {ocpp_message}")

    # Send the OCPP message via WebSocket client and await the response
    ocpp_response = await send_ocpp_message(ocpp_message)

    # You can process the ocpp_response here and include it in the HTTP response if needed
    # For this example, we'll just return a simple confirmation
    response_message = {"status": "success", "message": "Attempted to start charging via OCPP", "ocpp_client_response": ocpp_response}
    return jsonify(response_message)


@app.route('/stop_charging', methods=['POST'])
async def stop_charging_http():
    logging.info("Received HTTP request to /stop_charging")
    request_data = await request.get_json() or {} # Get request body if JSON

    # Extract relevant data from the HTTP request body for the OCPP message
    # This is an example mapping; adjust based on your HTTP request structure
    transaction_id = request_data.get("transactionId")
    meter_stop = request_data.get("meterStop")
    timestamp = request_data.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z")
    id_tag = request_data.get("idTag") # Optional in StopTransaction.req but useful


    # Basic validation
    if transaction_id is None or meter_stop is None:
         response_message = {"status": "error", "message": "Missing transactionId or meterStop in request body"}
         return jsonify(response_message), 400


    # Prepare the OCPP StopTransaction.req message (OCPP 1.6J format)
    ocpp_message = [
        2, # MessageTypeId: Call
        str(datetime.datetime.now().timestamp()), # Generate a unique MessageId
        "StopTransaction", # Action
        { # Payload
            "transactionId": transaction_id,
            "meterStop": meter_stop,
            "timestamp": timestamp, # Use the provided timestamp or generated
            # You can add other optional fields like "idTag", "transactionData" here
            "idTag": id_tag # Including idTag if available
        }
    ]
    # Remove idTag if it's None to match OCPP spec stricter interpretation for StopTransaction.req
    if "idTag" in ocpp_message[3] and ocpp_message[3]["idTag"] is None:
        del ocpp_message[3]["idTag"]


    logging.info(f"Attempting to send OCPP StopTransaction message via WebSocket client: {ocpp_message}")

    # Send the OCPP message via WebSocket client and await the response
    ocpp_response = await send_ocpp_message(ocpp_message)


    # You can process the ocpp_response here and include it in the HTTP response if needed
    # For this example, we'll just return a simple confirmation
    response_message = {"status": "success", "message": "Attempted to stop charging via OCPP", "ocpp_client_response": ocpp_response}
    return jsonify(response_message)


@app.route('/')
async def index():
    logging.info("Received HTTP request for index page")
    return "Dummy CMS Server is running (HTTP and OCPP enabled, using SQLite via Quart)"

# --- Updated HTTP GET Route for Sessions (reads from DB via database.py) ---
@app.route('/sessions', methods=['GET'])
async def list_sessions():
    logging.info("Received HTTP GET request for /sessions")
    sessions_list = get_all_sessions() # Use the function from database.py
    logging.info(f"Returning {len(sessions_list)} sessions from database.")
    # Convert datetime objects in sessions_list to string for JSON serialization
    for session in sessions_list:
        if isinstance(session.get('timestampStart'), datetime.datetime):
            session['timestampStart'] = session['timestampStart'].isoformat() + "Z"
        if isinstance(session.get('timestampStop'), datetime.datetime):
             session['timestampStop'] = session['timestampStop'].isoformat() + "Z"
        # Ensure transactionId is serializable if needed, though it should be int


    return jsonify(sessions_list)

# --- New OCPP 1.6J WebSocket Route using Quart ---
@app.websocket('/ocpp')
async def ocpp_websocket():
    logging.info("OCPP WebSocket connection established")

    while True: # Keep the connection open
        try:
            message = await websocket.receive() # Receive message from charge point

            if message is None:
                logging.debug("Received None message, connection might be closing.")
                continue # Continue loop, let Quart handle the actual close

            logging.info(f"Received OCPP message: {message}")

            try:
                # OCPP messages are JSON arrays: [MessageTypeId, MessageId, Action, Payload]
                # MessageTypeId: 2 for Call, 3 for CallResult, 4 for CallError
                ocpp_message = json.loads(message)
                message_type_id = ocpp_message[0]
                message_id = ocpp_message[1]
                action = ocpp_message[2]
                payload = ocpp_message[3]

                # Handle specific OCPP actions
                if action == "StartTransaction":
                    logging.info(f"Handling StartTransaction.req (MessageId: {message_id}) with payload: {payload})")
                    id_tag = payload.get("idTag")
                    meter_start = payload.get("meterStart", 0)
                    # Use current UTC time if not provided in payload - database function handles this or we pass it
                    # Ensure timestamp from payload is used if present
                    timestamp_str = payload.get("timestamp")
                    if timestamp_str:
                        try:
                            # Attempt to parse timestamp if provided
                             timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except ValueError:
                             logging.warning(f"Invalid timestamp format received: {timestamp_str}. Using current UTC time.")
                             timestamp = datetime.datetime.utcnow()
                    else:
                         timestamp = datetime.datetime.utcnow() # Use current UTC if not provided


                    if id_tag:
                        # Use create_session function from database.py
                        transaction_id = create_session(id_tag, timestamp.isoformat() + "Z", meter_start) # Pass ISO 8601 string with Z


                        logging.info(f"Created new session via database.py. Mock TransactionId: {transaction_id}")

                        # Construct StartTransaction.conf response
                        response_payload = {
                            "idTagInfo": {
                                "status": "Accepted"
                            },
                            "transactionId": transaction_id # Use the DB row ID as mock transactionId
                        }
                        # Construct the response message: [3, MessageId, Payload] for CallResult
                        response_message = [3, message_id, response_payload]
                        logging.info(f"Sending StartTransaction.conf response: {response_message}")
                        await websocket.send(json.dumps(response_message))
                    else:
                        logging.warning("StartTransaction.req received without idTag.")
                        # Send a CallError for missing required payload
                        error_message = [4, message_id, "ProtocolError", "Missing required payload field: idTag", {}]
                        await websocket.send(json.dumps(error_message))


                elif action == "StopTransaction":
                    logging.info(f"Handling StopTransaction.req (MessageId: {message_id}) with payload: {payload})")
                    transaction_id = payload.get("transactionId")
                    meter_stop = payload.get("meterStop")
                     # Use current UTC time if not provided in payload
                    # Ensure timestamp from payload is used if present
                    timestamp_str = payload.get("timestamp")
                    if timestamp_str:
                         try:
                              # Attempt to parse timestamp if provided
                              timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                         except ValueError:
                              logging.warning(f"Invalid timestamp format received: {timestamp_str}. Using current UTC time.")
                              timestamp = datetime.datetime.utcnow()
                    else:
                         timestamp = datetime.datetime.utcnow() # Use current UTC if not provided

                    # Add other relevant fields from payload if needed, e.g., idTag, transactionData


                    if transaction_id is not None and meter_stop is not None:
                        # Use update_session function from database.py
                        update_session(transaction_id, timestamp.isoformat() + "Z", meter_stop) # Pass ISO 8601 string with Z


                        logging.info(f"Updated session {transaction_id} via database.py.")

                        # Construct StopTransaction.conf response
                        response_payload = {
                            "idTagInfo": {
                                 "status": "Accepted" # Simulate accepting the stop
                            },
                             "meterStop": meter_stop # Include meterStop from request
                             # Add other relevant fields like transactionData if implemented
                        }
                        # Construct the response message: [3, MessageId, Payload] for CallResult
                        response_message = [3, message_id, response_payload]
                        logging.info(f"Sending StopTransaction.conf response: {response_message}")
                        await websocket.send(json.dumps(response_message))
                    else:
                        logging.warning("StopTransaction.req received without required fields (transactionId or meterStop).")
                         # Send a CallError for missing required payload
                        error_message = [4, message_id, "ProtocolError", "Missing required payload fields", {}]
                        await websocket.send(json.dumps(error_message))


                elif action == "BootNotification":
                     logging.info(f"Handling BootNotification.req (MessageId: {message_id}) with payload: {payload})")
                     # Mock BootNotification.conf response
                     response_payload = {
                         "currentTime": datetime.datetime.utcnow().isoformat() + "Z", # Ensure Z for UTC
                         "interval": 300, # Recommended heartbeat interval in seconds
                         "status": "Accepted"
                     }
                     response_message = [3, message_id, response_payload]
                     logging.info(f"Sending BootNotification.conf response: {response_message}")
                     await websocket.send(json.dumps(response_message))

                elif action == "Heartbeat":
                     logging.info(f"Handling Heartbeat.req (MessageId: {message_id})")
                     # Mock Heartbeat.conf response
                     response_payload = {
                         "currentTime": datetime.datetime.utcnow().isoformat() + "Z" # Ensure Z for UTC
                     }
                     response_message = [3, message_id, response_payload]
                     logging.info(f"Sending Heartbeat.conf response: {response_message}")
                     await websocket.send(json.dumps(response_message))


                else:
                    logging.warning(f"Unknown or unhandled OCPP action received: {action}")
                    # Send a CallError response for unknown actions
                    error_message = [4, message_id, "NotImplemented", f"Unknown action: {action}", {}]
                    await websocket.send(json.dumps(error_message))

            except json.JSONDecodeError:
                logging.error(f"Failed to decode JSON message: {message}")
                 # Cannot send a valid CallError if message_id is unknown

            except IndexError:
                 logging.error(f"Received malformed OCPP message (not enough elements): {message}")
                 # Cannot send a valid CallError if message_id is unknown

            except Exception as e:
                logging.error(f"An error occurred while processing message (MessageId: {message_id if 'message_id' in locals() else 'unknown'}): {e}", exc_info=True)
                 # Attempt to send CallError if message_id was successfully parsed
                if 'message_id' in locals():
                     error_message = [4, message_id, "InternalError", f"Server error: {e}", {}]
                     try:
                         await websocket.send(json.dumps(error_message))
                     except Exception as send_error:
                         logging.error(f"Failed to send CallError response: {send_error}")

        except Exception as e: # Catch exceptions during receive or send
             logging.error(f"Error in WebSocket communication: {e}", exc_info=True)
             break # Exit the loop and close the connection

    logging.info("OCPP WebSocket connection closed")


if __name__ == '__main__':
    logging.info("Starting Dummy CMS Server with HTTP, OCPP (Quart), and SQLite (using database.py)...")
    # Quart applications are typically run using an ASGI server like hypercorn
    # We installed hypercorn as a dependency of Quart
    # app.run() is a simple way to run for development
    app.run(port=5050, debug=True) # Use debug=True for development, it auto-reloads
