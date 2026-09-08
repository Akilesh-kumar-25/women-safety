# Women's Safety App

A modern, full-stack web application designed for women's safety. This application features an intelligent voice-activated SOS system that can instantly record emergency video, capture live GPS location, and broadcast an emergency MMS/SMS to designated contacts.

## Features
- **Voice-Activated SOS:** Continuously listens for the keyword "help". Triggering it twice instantly activates the emergency protocol.
- **Strict Permission System:** Enforces Camera, Microphone, and Location permissions before granting access to the dashboard.
- **Cloudinary Integration:** Automatically uploads emergency video recordings securely to the cloud.
- **Twilio Integration:** Instantly sends emergency alerts to trusted contacts via SMS with a live Google Maps location and a playable video link.
- **Persistent Contacts:** Securely stores your emergency contacts locally with country-code support.

## Tech Stack
- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI, Uvicorn
- **Third-Party Services:** Twilio (SMS), Cloudinary (Video Hosting), Google Maps (Live Location)

## Setup Instructions

### 1. Prerequisites
- Node.js (v16+)
- Python (3.9+)
- Twilio Account (for SMS)
- Cloudinary Account (for Video Uploads)

### 2. Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the `backend/` directory and add your credentials:
   ```env
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_FROM_NUMBER=your_twilio_phone_number
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   FIREBASE_WEB_API_KEY=your_firebase_api_key
   ```
4. Run the backend server:
   ```bash
   uvicorn main:app --reload
   ```

### 3. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

## Usage
1. Open the frontend in your browser.
2. Grant the required Camera, Microphone, and Location permissions.
3. Add your emergency contacts to the dashboard.
4. Shout **"Help!"** twice to trigger the SOS protocol. The system will record a 30-second video, fetch your live GPS coordinates, and text your contacts automatically.

## Important Note
This repository does not contain any sensitive API keys or database files. You must provide your own API keys in the `.env` file for the application to function properly.
