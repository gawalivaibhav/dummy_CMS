import logging
import json
import datetime
# Import Quart specific modules
from quart import Quart, websocket, jsonify, request, Response # Added request and Response

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

# --- HTTP Routes ---
# Using async def for routes as Quart is asynchronous
@app.route('/start_charging', methods=['POST'])
async def start_charging_http():
    logging.info("Received HTTP request to start charging (NOTE: HTTP routes are separate from OCPP)")
    # In a real scenario, you'd process request data and logic here
    # For this dummy route, just return a mock response
    return jsonify({"status": "success", "message": "Charging started (dummy via HTTP)"})

@app.route('/stop_charging', methods=['POST'])
async def stop_charging_http():
    logging.info("Received HTTP request to stop charging (NOTE: HTTP routes are separate from OCPP)")
    # In a real scenario, you'd process request data and logic here
    # For this dummy route, just return a mock response
    return jsonify({"status": "success", "message": "Charging stopped (dummy via HTTP)"})

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
                    timestamp = payload.get("timestamp", datetime.datetime.utcnow().isoformat())


                    if id_tag:
                        # Use create_session function from database.py
                        transaction_id = create_session(id_tag, timestamp, meter_start)

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
                    timestamp = payload.get("timestamp", datetime.datetime.utcnow().isoformat())
                    # Add other relevant fields from payload if needed, e.g., idTag, transactionData

                    if transaction_id is not None and meter_stop is not None:
                        # Use update_session function from database.py
                        update_session(transaction_id, timestamp, meter_stop)

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
