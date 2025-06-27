import asyncio
import websockets
import json
import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_connection():
    uri = "ws://localhost:5050/ocpp"
    try:
        logging.info(f"Attempting to connect to {uri}")
        async with websockets.connect(uri) as websocket:
            logging.info(f"Successfully connected to {uri}")
            # Connection established, now just close it
            logging.info("Connection successful, closing now.")
            await websocket.close() # Explicitly close the connection

    except ConnectionRefusedError:
        logging.error(f"Connection refused. Is the server running at {uri}?")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    # Ensure your dummy CMS server is running before running this script
    asyncio.run(test_connection())

