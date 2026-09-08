from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import socket
import uuid
import requests
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

# The Web API Key provided by the user for Auth REST API
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

# Try to initialize Firebase Admin (For Firestore Database)
try:
    if os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Admin Initialized Successfully!")
    else:
        db = None
        print("WARNING: serviceAccountKey.json not found. Database will be simulated in-memory.")
except Exception as e:
    db = None
    print(f"WARNING: Firebase Admin initialization failed: {e}")

# In-memory mock DB fallback (Reset for user)
DB_FILE = "db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

mock_db = load_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ContactRequest(BaseModel):
    uid: str
    name: str
    phone: str
    relation: str

class EditContactRequest(BaseModel):
    name: str
    phone: str
    relation: str

@app.get("/api/hello")
def hello():
    return {"message": "Python Backend is up and running!"}

# --- AUTHENTICATION ENDPOINTS (Using Firebase REST API) ---

@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    name_lower = req.name.strip().lower()
    
    # Check if name is taken
    is_taken = False
    if db:
        docs = db.collection("users").where("name_lower", "==", name_lower).limit(1).get()
        if docs:
            is_taken = True
    else:
        for uid, user_data in mock_db.items():
            if user_data.get("name_lower") == name_lower:
                is_taken = True
                break
                
    if is_taken:
        suggested_name = f"{req.name.strip()}123"
        raise HTTPException(status_code=400, detail=f"'{req.name}' is already taken. Why not try '{suggested_name}'?")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": req.email,
        "password": req.password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"]["message"])
        
    uid = data["localId"]
    
    # Save user name
    user_info = {"name": req.name.strip(), "name_lower": name_lower, "email": req.email}
    if db:
        db.collection("users").document(uid).set(user_info)
    else:
        mock_db[uid] = user_info
        save_db(mock_db)
        
    return {"uid": uid, "name": req.name.strip(), "email": data["email"], "token": data["idToken"]}

@app.post("/api/auth/login")
def login(req: LoginRequest):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": req.email,
        "password": req.password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"]["message"])
        
    uid = data["localId"]
    name = "User"
    
    # Retrieve name
    if db:
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            name = doc.to_dict().get("name", "User")
    else:
        user_info = mock_db.get(uid, {})
        name = user_info.get("name", "User")
        
    return {"uid": uid, "name": name, "email": data["email"], "token": data["idToken"]}


# --- DATABASE ENDPOINTS ---

@app.get("/api/contacts/{uid}")
def get_contacts(uid: str):
    name = "User"
    contacts = []
    
    if db:
        user_doc = db.collection("users").document(uid).get()
        if user_doc.exists:
            name = user_doc.to_dict().get("name", "User")
            
        docs = db.collection("users").document(uid).collection("contacts").stream()
        contacts = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    else:
        user_info = mock_db.get(uid, {})
        name = user_info.get("name", "User")
        contacts = user_info.get("contacts", [])
        
    return {"name": name, "contacts": contacts}

@app.post("/api/contacts")
def add_contact(req: ContactRequest):
    contact_data = {
        "name": req.name,
        "phone": req.phone,
        "relation": req.relation
    }
    if db:
        new_ref = db.collection("users").document(req.uid).collection("contacts").document()
        new_ref.set(contact_data)
        contact_data["id"] = new_ref.id
        return {"success": True, "contact": contact_data}
    else:
        # Fallback to mock
        contact_data["id"] = uuid.uuid4().hex
        if req.uid not in mock_db:
            mock_db[req.uid] = {"contacts": []}
        if "contacts" not in mock_db[req.uid]:
            mock_db[req.uid]["contacts"] = []
            
        mock_db[req.uid]["contacts"].append(contact_data)
        save_db(mock_db)
        return {"success": True, "contact": contact_data}

@app.put("/api/contacts/{uid}/{contact_id}")
def edit_contact(uid: str, contact_id: str, req: EditContactRequest):
    update_data = {
        "name": req.name,
        "phone": req.phone,
        "relation": req.relation
    }
    
    if db:
        ref = db.collection("users").document(uid).collection("contacts").document(contact_id)
        if ref.get().exists:
            ref.update(update_data)
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Contact not found")
    else:
        user_info = mock_db.get(uid)
        if not user_info or "contacts" not in user_info:
            raise HTTPException(status_code=404, detail="User or contacts not found")
            
        for contact in user_info["contacts"]:
            if contact["id"] == contact_id:
                contact.update(update_data)
                save_db(mock_db)
                return {"success": True}
                
        raise HTTPException(status_code=404, detail="Contact not found")


# --- EMERGENCY ENDPOINT ---

@app.post("/api/send-alert")
async def send_alert(
    latitude: str = Form(...),
    longitude: str = Form(...),
    message: str = Form(...),
    recipients: str = Form(...),
    video: UploadFile = File(...)
):
    try:
        contact_emails = json.loads(recipients)
        video_filename = f"emergency_{uuid.uuid4().hex}.webm"
        video_content = await video.read()
        
        os.makedirs("uploads", exist_ok=True)
        local_path = os.path.join("uploads", video_filename)
        with open(local_path, "wb") as f:
            f.write(video_content)
            
        print(f"Alert triggered! Video saved to {local_path}.")
        
        # --- TWILIO SMS INTEGRATION ---
        TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
        
        try:
            from twilio.rest import Client
            import cloudinary
            import cloudinary.uploader
            
            # --- CLOUDINARY INTEGRATION ---
            cloudinary.config(
                cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key = os.getenv("CLOUDINARY_API_KEY"),
                api_secret = os.getenv("CLOUDINARY_API_SECRET"),
                secure = True
            )
            
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Attempt to upload to Cloudinary for a permanent, global, playable URL
            try:
                upload_result = cloudinary.uploader.upload(
                    local_path, 
                    resource_type="video",
                    folder="emergency_alerts"
                )
                video_url = upload_result.get("secure_url")
                print(f"Cloudinary upload successful! URL: {video_url}")
            except Exception as e:
                print(f"Cloudinary upload failed. Falling back to Local IP. Error: {e}")
                local_ip = get_local_ip()
                video_url = f"http://{local_ip}:8000/uploads/{video_filename}"
                
            sms_body = f"EMERGENCY SOS: Help is needed!\nLocation: https://www.google.com/maps/search/?api=1&query={latitude},{longitude}\nVideo: {video_url}"
            
            for phone_number in contact_emails:
                if not phone_number.startswith('+'):
                    phone_number = "+91" + phone_number 
                
                # Send the SMS as a standard text message
                message_args = {
                    "body": sms_body,
                    "from_": TWILIO_FROM_NUMBER,
                    "to": phone_number
                }
                
                message = client.messages.create(**message_args)
                print(f"SMS sent to {phone_number}, SID: {message.sid}")
        except Exception as twilio_err:
            print(f"Twilio SMS Error: {twilio_err}")
            
        return {"success": True, "message": "Alert logged and processed successfully!"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
