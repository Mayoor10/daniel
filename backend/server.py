from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO
import os
from pymongo import MongoClient
import datetime
from bson.json_util import dumps

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://localhost:5173"]}})


# Initialize MongoDB client with the connection string provided by MongoDB Atlas
# Replace 'YOUR_CONNECTION_STRING' with the connection string provided by MongoDB Atlas
client = MongoClient('mongodb+srv://itb08mayoormoolya:YwUiZLL1z394pIsY@cluster0.vzelppo.mongodb.net/')

# Access your database
db = client['attendance_management']  # Replace 'your_database_name' with your actual database name

# Assuming you have a YOLO model initialized and configured
model_path = os.path.join('.', 'train14', 'weights', 'last.pt')
model = YOLO(model_path)

def detect_objects(image):
    results = model(image)[0]

    threshold = 0.5
    class_names = ['rohan', 'sarita']

    detection_results = []
    class_presence = {class_name: "Absent" for class_name in class_names}

    for result in results.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = result

        if score > threshold:
            class_name = class_names[int(class_id)]
            class_presence[class_name] = "Present"
            detection_results.append({
                "class_name": class_name,
                "bounding_box": [x1, y1, x2, y2]
            })

    # Check if no objects are detected
    if not detection_results:
        return {"message": "No classes detected"}

    # Return class presence in JSON format
    return {"detection_results": detection_results, "class_presence": class_presence}

@app.route("/")
def home():
    return {"message": "Hello from backend"}

@app.route("/upload", methods=['POST'])
def upload():
    file = request.files['file']
    file.save('uploads/' + file.filename)

    # Read an image from the provided path
    img_path = f"./uploads/{file.filename}" 
    image = cv2.imread(img_path)

    if image is None:
        return jsonify({"message": "Error: Unable to read the image"}), 400

    # Perform object detection
    detection_result = detect_objects(image)

    # Store detection results in MongoDB
    detections_collection = db["detections"]
    detections_collection.insert_one({
        "detection_results": detection_result["detection_results"],
        "class_presence": detection_result["class_presence"],
        "timestamp": datetime.datetime.now()
    })

    if os.path.exists(f"./uploads/{file.filename}"):
        os.remove(f"uploads/{file.filename}")

    return jsonify(detection_result)

@app.route('/attendance')
def get_attendance_data():
    # Assuming your MongoDB collection name is 'detections'
    attendance_collection = db['detections']
    # Query the collection and convert the cursor to a list of dictionaries
    data = list(attendance_collection.find())
    # Convert ObjectId to string and timestamp to ISO format
    for entry in data:
        entry['_id'] = str(entry['_id'])
        entry['timestamp'] = entry['timestamp'].isoformat()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=3001)
