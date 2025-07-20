# Voice Agent Prototype

This project is a functional prototype of a Finnish-speaking voice agent designed for booking healthcare appointments. It demonstrates a basic conversational flow, from greeting the user to confirming a booking, all handled through a simple web interface.

This README provides instructions on how to set up and run the prototype, outlines the technical architecture, and discusses the assumptions and simplifications made during development.

## Features

- **Voice-driven interaction**: The primary interface is voice-based, allowing users to speak their requests naturally.
- **Finnish language support**: All interactions, including speech-to-text and text-to-speech, are in Finnish.
- **Appointment booking flow**: The agent guides the user through a structured conversation to book an appointment, including:
    - Greeting the user
    - Identifying the desired appointment type (e.g., dentist, hygienist)
    - Suggesting available time slots
    - Capturing the user's name
    - Confirming the booking details
- **Fuzzy matching**: The agent uses modern sentence transformers to understand user intent, even when the phrasing doesn't exactly match predefined keywords.
- **Persistent storage**: Confirmed bookings are saved to a `bookings.json` file.

## Architecture and Tech Stack

This prototype is built as a single Python service using the FastAPI framework. While the `ARCHITECTURE.md` file describes a scalable, production-ready system based on microservices, this prototype simplifies that vision into a single, self-contained application.

### Key Components

- **Backend**: A FastAPI server handles all incoming requests, manages the conversation state, and orchestrates the AI models.
- **Frontend**: A simple HTML page with JavaScript allows the user to record their voice and interact with the agent.
- **Speech-to-Text (STT)**: `faster-whisper` is used to transcribe the user's Finnish speech into text.
- **Text-to-Speech (TTS)**: `facebook/mms-tts-fin` converts the agent's text responses into audible speech.
- **Natural Language Understanding (NLU)**:
    - **Intent Recognition**: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` is used for zero-shot classification to identify the user's desired appointment type.
    - **Confirmation Handling**: `paraphrase-multilingual-MiniLM-L12-v2` is used as a sentence transformer to robustly interpret "yes/no" confirmations.

### Tech Stack Summary

- **Programming Language**: Python 3.13
- **Web Framework**: FastAPI
- **AI/ML Libraries**:
    - `transformers`
    - `faster-whisper`
    - `sentence-transformers`
    - `torch`
- **Dependency Management**: Poetry

## How to Run and Test the Prototype

To get the prototype running locally, follow these steps:

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/TapioIkimaa/voice-agent.git
    cd voice-agent
    ```

2.  **Install dependencies**:

    Make sure you have Python 3.13 and Poetry installed. Then, run:

    ```bash
    poetry install
    ```

3.  **Run the application**:

    ```bash
    poetry run uvicorn main:app
    ```

4.  **Open the web interface**:

    Navigate to `http://localhost:8000` in your web browser.

5.  **Interact with the agent**:

    - Click the "Record" button and speak into your microphone.
    - Follow the agent's prompts to book an appointment.
    - Once confirmed, the booking will be saved in the `bookings.json` file in the project's root directory.

## Assumptions and Simplifications

In the interest of rapid prototyping, several simplifications were made:

- **Single-user focus**: The conversation state is managed in-memory and is not designed to handle multiple concurrent users.
- **Hardcoded data**: Available appointment slots are hardcoded in the `main.py` file, rather than being fetched from a live database or external API.
- **Simplified error handling**: The error handling is basic and does not cover all edge cases.
- **No real booking integration**: The prototype saves bookings to a local JSON file instead of integrating with a real-world booking system.
- **Local AI models**: All models are loaded and run locally. In a production environment, these would likely be managed as separate, scalable services as described in `ARCHITECTURE.md`.
- **Non-streamed interaction**: The user records their entire message, which is then processed. In a production system, the audio would be streamed to the STT service in real-time to reduce latency.

## Demonstration video

https://github.com/user-attachments/assets/ea2c9f56-3811-4415-9f94-bdd629a449a1
