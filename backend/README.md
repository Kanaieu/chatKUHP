# FastAPI Chatbot Application

This project is a FastAPI application that serves as a chatbot for legal inquiries. It utilizes the Google GenAI client to process user queries and generate responses based on a knowledge base of legal information.

## Project Structure

```
fastapi-chatbot-app
├── routes
│   └── chat.py          # Defines the routing for the chatbot endpoint
├── services
│   ├── gog_graph        # Contains knowledge base files for legal information
│   │   ├── kb_kuhp.pkl
│   │   ├── kb.pkl
│   │   └── temp_batch_emb.jsonl
│   ├── .env             # Environment variables for the application
│   ├── build_runner.py   # Script for building the application
│   ├── gog_chatbot.py    # Contains the PlanningModel class for processing queries
│   ├── gog_data.py      # Data handling for the application
│   ├── gog_notebook.ipynb # Jupyter notebook for experimentation
│   ├── gog_prompts.py    # Contains prompt templates for the chatbot
│   ├── schemas.py       # Data schemas for validation
│   └── test_embed.py    # Testing utilities for embedding
├── Dockerfile            # Dockerfile for containerizing the application
├── main.py              # Entry point of the FastAPI application
├── requirements.txt      # Python dependencies for the project
└── README.md            # Documentation for the project
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd fastapi-chatbot-app
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the `services` directory and add your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

5. **Run the application:**
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Usage

- The chatbot endpoint can be accessed at `http://localhost:8000/chat`.
- Send a POST request with a JSON body containing the user's query to receive a legal analysis.

## Docker

To build and run the application using Docker, follow these steps:

1. **Build the Docker image:**
   ```
   docker build -t fastapi-chatbot-app .
   ```

2. **Run the Docker container:**
   ```
   docker run -d -p 8000:8000 fastapi-chatbot-app
   ```

## License

This project is licensed under the MIT License. See the LICENSE file for more details.