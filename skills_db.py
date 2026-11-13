"""Static skill knowledge from resume_skills_crafter.md (sections 3-4).

Everything here is literal-string data: ATS matching is keyword based, so a skill
is "present" only if one of its spellings appears in the resume text.
"""

# canonical -> extra spellings (the canonical itself is always a spelling)
SKILLS: dict[str, list[str]] = {
    # languages
    "Python": [], "Java": [], "JavaScript": [], "TypeScript": [], "C++": [], "C": [],
    "SQL": [], "Go": ["golang"], "Rust": [], "Scala": [], "Kotlin": [], "R": [],
    "Shell Scripting": ["bash", "shell"],
    # frontend / mobile
    "React": ["react.js", "reactjs"], "Next.js": ["nextjs", "next js"],
    "Vue.js": ["vue", "vuejs"], "Angular": [], "HTML": ["html5"], "CSS": ["css3"],
    "Tailwind CSS": ["tailwind"], "Redux": [], "Zustand": [], "React Native": [],
    "Expo": [], "Bootstrap": [], "Material UI": ["mui"],
    # backend
    "FastAPI": [], "Flask": [], "Django": [], "Node.js": ["nodejs", "node js"],
    "Express": ["express.js", "expressjs"],
    "Spring Boot": ["java spring boot", "springboot", "spring"],
    "REST APIs": ["rest api", "restful apis", "restful api", "restful", "REST"],
    "GraphQL": [], "WebSockets": ["websocket", "web sockets"],
    "Socket.IO": ["socketio"], "gRPC": [], "Microservices": ["microservice"],
    "JWT": ["json web token", "json web tokens"], "OAuth 2.0": ["oauth", "oauth2"],
    "Hibernate": [], "JPA": [], "Swagger": ["openapi"], "Postman": [],
    "Mongoose": [],
    # databases
    "MySQL": [], "PostgreSQL": ["postgres"], "MongoDB": ["mongo"], "Redis": [],
    "Supabase": [], "Firebase": ["firebase realtime db"], "SQLite": [],
    "Elasticsearch": [], "DynamoDB": [], "NoSQL": [],
    # AI / ML
    "PyTorch": [], "TensorFlow": [], "Keras": [],
    "Scikit-learn": ["sklearn", "scikit learn"], "Pandas": [], "NumPy": [],
    "Transformers": [], "Hugging Face": ["huggingface"],
    "LLMs": ["llm", "large language models", "large language model"],
    "RAG": ["rag pipelines", "retrieval-augmented generation",
            "retrieval augmented generation"],
    "LangChain": [], "LangGraph": [], "LlamaIndex": [],
    "Vector Databases": ["vector database", "vector db", "vector dbs",
                         "vector store", "vector stores"],
    "FAISS": [], "ChromaDB": ["chroma"], "Pinecone": [], "pgvector": [],
    "Embeddings": ["embedding"], "Semantic Search": [],
    "Prompt Engineering": [], "OpenAI API": ["openai", "openai apis"],
    "Gemini": ["google gemini"], "AI Agents": ["ai agent", "agentic", "agentic ai"],
    "Tool Calling": ["function calling"],
    "MCP": ["mcp tools", "model context protocol"],
    "Fine-tuning": ["finetuning", "fine tuning", "whisper fine-tuning"],
    "NLP": ["natural language processing"], "Computer Vision": [],
    "Speech Recognition": ["asr", "speech-to-text", "speech to text"],
    "Voice Agents": ["voice agent"], "MLflow": [], "RAGAS": [], "Langfuse": [],
    "LangSmith": [], "Streamlit": [], "Gradio": [], "Jupyter": ["jupyter notebook"],
    "Generative AI": ["genai", "gen ai"], "Deep Learning": [],
    "Machine Learning": ["ml"], "MLOps": [],
    "Data Cleaning": ["data preprocessing", "data pre-processing"],
    "Knowledge Base": [], "Information Retrieval": [], "Face Recognition": [],
    # tools / devops
    "Git": [], "GitHub": [], "Docker": [], "Kubernetes": ["k8s", "kubectl"],
    "CI/CD": ["cicd", "ci cd", "github actions", "continuous integration"],
    "Linux": ["unix"], "AWS": ["amazon web services"], "Azure": [],
    "GCP": ["google cloud"], "Jenkins": [], "Kibana": [], "Selenium": [],
    "Claude Code": [], "Jest": [], "PyTest": [], "JUnit": [],
    "React Testing Library": [], "Vercel": [], "Netlify": [],
    "Agile": ["scrum"], "Unit Testing": ["unit tests"],
    "Web Scraping": ["web automation"],
    # A3 style experience keywords
    "Authentication": ["authorization", "auth"],
    "RBAC": ["role-based access control", "role based access control"],
    "Database Schema Design": ["schema design"],
    "Query Optimization": ["query tuning"],
    "Production Debugging": [], "Log Analysis": [],
    "Third-party API Integration": ["api integration", "third party api",
                                    "third-party apis"],
    "Push Notifications": [], "FCM": ["firebase cloud messaging"],
    "Leaflet": [], "Geospatial": ["openstreetmap"], "Real-time Systems": [],
    # CS fundamentals
    "Data Structures & Algorithms": ["dsa", "data structures", "algorithms"],
    "OOP": ["object oriented programming", "object-oriented programming", "oops"],
    "DBMS": [], "SDLC": [], "System Design": [],
    # tier C only
    "CUDA": [], "Distributed Training": [], "Reinforcement Learning": [],
    "Kafka": [], "Spark": ["apache spark", "pyspark"], "Hadoop": [],
    "Terraform": [], "Helm": [],
}

# spellings that must match case-sensitively (too ambiguous in plain English)
CASE_SENSITIVE = {"C", "R", "Go", "Express", "ML", "Spring", "REST"}

# Tier A3: proven in resume bullets but not in the skills section -> free to add
TIER_A3 = {
    "Embeddings", "Semantic Search", "Speech Recognition", "Fine-tuning",
    "Hugging Face", "NLP", "Prompt Engineering", "Data Cleaning", "Knowledge Base",
    "Information Retrieval", "Face Recognition", "Authentication", "RBAC",
    "Database Schema Design", "Query Optimization", "Production Debugging",
    "Log Analysis", "Third-party API Integration", "Push Notifications", "FCM",
    "Leaflet", "Geospatial", "Microservices", "Web Scraping", "Real-time Systems",
}

# Tier C: never add (weeks to learn / easily exposed)
TIER_C = {
    "CUDA", "Distributed Training", "Reinforcement Learning", "Kafka", "Spark",
    "Hadoop", "System Design", "Rust", "Go", "Scala", "Computer Vision",
    "Terraform", "Helm",
}

# Tier B per role family: (skill, frequency, hours-to-basics)  freq: H / MH / M / L
TIER_B = {
    "ai": [
        ("LangChain", "H", 4), ("Vector Databases", "H", 3), ("OpenAI API", "H", 2),
        ("Docker", "H", 4), ("LangGraph", "MH", 4), ("AI Agents", "MH", 4),
        ("Tool Calling", "MH", 4), ("LlamaIndex", "M", 3), ("TensorFlow", "M", 5),
        ("Streamlit", "M", 2), ("Gradio", "M", 2), ("Jupyter", "M", 0),
        ("AWS", "M", 5), ("RAGAS", "L", 3), ("MLflow", "L", 3),
        ("Langfuse", "L", 2), ("LangSmith", "L", 2), ("FAISS", "M", 3),
        ("ChromaDB", "M", 3), ("pgvector", "M", 3), ("Pinecone", "L", 2),
    ],
    "sde": [
        ("Docker", "H", 4), ("Linux", "H", 3), ("PostgreSQL", "H", 2),
        ("CI/CD", "MH", 3), ("Redis", "M", 3), ("JWT", "M", 2), ("OAuth 2.0", "M", 2),
        ("Postman", "M", 1), ("Swagger", "M", 1), ("JUnit", "M", 3),
        ("PyTest", "M", 3), ("Hibernate", "M", 4), ("JPA", "M", 4),
        ("AWS", "M", 5), ("Agile", "M", 1),
    ],
    "fullstack": [
        ("TypeScript", "H", 4), ("Tailwind CSS", "H", 2), ("Redux", "MH", 3),
        ("Zustand", "MH", 3), ("PostgreSQL", "M", 2), ("Docker", "M", 4),
        ("JWT", "M", 2), ("OAuth 2.0", "M", 2), ("Socket.IO", "M", 1),
        ("Jest", "M", 3), ("React Testing Library", "M", 3), ("Vercel", "M", 1),
        ("Netlify", "M", 1), ("Mongoose", "M", 1), ("GraphQL", "L", 4),
        ("Expo", "L", 1),
    ],
}
# adjacent tools not in the plan tables but clearly <=5h next to a known skill
EXTRA_B = {"Flask": ("M", 2), "SQLite": ("L", 1), "Bootstrap": ("L", 2),
           "GitHub": ("M", 1), "Unit Testing": ("M", 2), "Shell Scripting": ("M", 3),
           "Elasticsearch": ("L", 4)}

FREQ_SCORE = {"H": 4, "MH": 3, "M": 2, "L": 1}

# Tier-B frequencies that count as "an ATS for this role nearly always searches it"
IMPLIED_FREQ = {"H", "MH"}
