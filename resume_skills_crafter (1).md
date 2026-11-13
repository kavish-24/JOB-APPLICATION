# Resume Skills Crafter — Master Plan & LLM Instructions

**Owner:** Kavish Toraskar · B.E. IT (Data Science minor), Goa College of Engineering, 2026
**Purpose:** Given a **JD + role title + chosen resume variant**, rewrite **only the TECHNICAL SKILLS section** so the resume gets shortlisted more often by ATS keyword search/ranking and by the recruiter's quick scan.
**Who reads this file:** whichever LLM does the editing. Sections 1–4 give context. **Sections 5–9 are the operating instructions.**

---

## 1. Context and decisions so far

### 1.1 Goal
- The bottleneck is **getting shortlisted**, not converting interviews. The candidate has cleared interviews at 5 companies (fresher rounds are DSA + theory + projects).
- Target roles are **fresher / new-grad only**: AI/ML Engineer, Software Engineer (SDE), Full Stack Developer.
- Even a small lift in shortlist rate (around 5%) is worth it at application volume.

### 1.2 How ATS actually works (shapes the rules below)
- Most ATS (Workday, Greenhouse, Lever, iCIMS, Naukri recruiter search) **parse the PDF text layer**. They don't OCR. The bigger risk is a **parse failure** from tables, columns, icons, or text in images or headers.
- Many ATS work as a **searchable database**. Recruiters run boolean keyword searches with the JD's wording ("Python AND LangChain"), and some systems also rank applicants by match score.
- Matching is **literal on many systems**. "LLMs" might not match "Large Language Models", so include both forms for the important terms.
- Newer systems add **semantic matching** and weight a keyword higher when it appears in context (project bullets). The candidate chose to edit the **skills section only**, which is accepted. The tradeoff is that context weighting is left unused.
- JDs leave out skills the screener expects. If a JD says "Python" for an AI Engineer role, the recruiter may still search "LangChain" or "vector database". The **role → skill graph** (Section 4) surfaces these.

### 1.3 Decisions
| Decision | Status |
|---|---|
| Edit only the TECHNICAL SKILLS section | ✅ Final |
| Pick 1 of 3 resume variants per application | ✅ Final |
| Allowed to add skills not yet known, **only tool-level skills learnable in ≤5 h** (Tier B) | ✅ Final |
| Never add concept-heavy skills that need weeks to learn (Tier C) | ✅ Final |
| Every added Tier-B skill comes with a study sheet | ✅ Final |
| Skill graph v0 = LLM prior (Section 4); v1 = built from a real JD corpus | 🔜 Roadmap |
| Editing is done by another LLM following this file | ✅ Final |

---

## 2. The three resume variants

All three have **identical skill content**. Only the **category order** and the summary/project order change. Parse check: all three PDFs extract cleanly with `pdftotext` (single column, plain text, no tables). ✅

| Variant | Use for roles like | Skills category order |
|---|---|---|
| **AI/ML** | AI Engineer, ML Engineer, GenAI/LLM Engineer, Data Scientist (fresher), NLP/Speech Engineer | AI/ML → Languages → Backend → Databases → Frontend & Mobile → Tools & DevOps → CS Fundamentals |
| **SDE** | Software Engineer, SDE-1, Backend Developer, Java Developer, Python Developer, Graduate Engineer Trainee | Languages → Backend → Frontend & Mobile → Databases → AI/ML → Tools & DevOps → CS Fundamentals |
| **Full Stack** | Full Stack Developer, MERN Developer, Frontend/React Developer, Mobile (React Native) Developer | Languages → Frontend & Mobile → Backend → Databases → AI/ML → Tools & DevOps → CS Fundamentals |

**Selection rule:** choose by the JD's *primary* work, not just its title. An "SDE – AI Platform" JD that's mostly RAG/LLM work gets the AI/ML variant. If the JD is mixed, use SDE.

### 2.1 Current skills section (baseline, same in all three)
```
Languages: Python, Java, JavaScript, C++, C, SQL
Frontend & Mobile: React, Next.js, React Native, Vue.js, HTML, CSS
Backend: FastAPI, Node.js, Express, Java Spring Boot, REST APIs, WebSockets
Databases: MySQL, MongoDB, Supabase, Firebase Realtime DB
AI/ML: PyTorch, Transformers, Whisper fine-tuning, RAG pipelines, LLMs (Google Gemini), Voice Agents, VAD, Scikit-learn, Pandas, NumPy
Tools & DevOps: Git, Kubernetes (kubectl), Kibana, Selenium, Claude Code
CS Fundamentals: Data Structures & Algorithms, OOP, DBMS, SDLC
```

---

## 3. Skills database

### 3.1 Tiers (how the editing LLM classifies every skill)
| Tier | Meaning | Can add? |
|---|---|---|
| **A1 – Proven** | Listed AND backed by a job/project bullet | Always keep if relevant |
| **A2 – Listed only** | In the skills list, no bullet backs it | Keep if relevant, drop first when space is tight |
| **A3 – Earned but unlisted** | Clearly used in a bullet but **missing from the skills section**. Free keywords, no bluff. | ✅ Add freely when the JD wants them |
| **B – Adjacent tool** | Not on the resume, but one hop from an A skill and learnable to a basic level in **≤5 h** | ✅ Add max **4** per application, with study sheet |
| **C – Concept/heavy** | Needs weeks, or interviewers can trivially expose it (e.g. CUDA, Distributed Systems, Reinforcement Learning, Rust, Kafka internals, Computer Vision research) | ❌ Never add |

### 3.2 Tier A1 / A2 — currently listed
| Skill | Category | Tier | Evidence (where it's proven) |
|---|---|---|---|
| Python | Languages | A1 | FastAPI, Whisper fine-tuning, RAG, Selenium pipeline |
| Java | Languages | A1 | Spring Boot debugging @ Turtlemint |
| JavaScript | Languages | A1 | Node/Express @ Freethink, React Native, Next.js |
| SQL | Languages | A1 | MySQL schema redesign @ Freethink |
| C++ | Languages | A2 | No bullet (LeetCode/DSA language) |
| C | Languages | A2 | No bullet |
| React | Frontend | A2 | Implied by Next.js/React Native, no direct bullet |
| Next.js | Frontend | A1 | Document Assistant |
| React Native | Mobile | A1 | E-Bandobast app |
| Vue.js | Frontend | A2 | No bullet. **Drop first** when space is tight |
| HTML, CSS | Frontend | A2 | Implied |
| FastAPI | Backend | A2 | Mentioned in summary only, not in a bullet |
| Node.js, Express | Backend | A1 | Freethink, E-Bandobast |
| Java Spring Boot | Backend | A1 | Turtlemint (debugging production services) |
| REST APIs | Backend | A1 | Freethink, partner API integration @ Turtlemint |
| WebSockets | Backend | A1 | Real-time messaging @ Freethink |
| MySQL | Databases | A1 | Freethink |
| MongoDB | Databases | A1 | E-Bandobast |
| Supabase | Databases | A1 | Freethink, Document Assistant |
| Firebase Realtime DB | Databases | A1 | E-Bandobast live tracking |
| PyTorch | AI/ML | A1 | Document Assistant RAG |
| Transformers | AI/ML | A1 | Whisper fine-tuning |
| Whisper fine-tuning | AI/ML | A1 | AshwaasAI (WER 120 → 39) |
| RAG pipelines | AI/ML | A1 | Document Assistant, AshwaasAI |
| LLMs (Google Gemini) | AI/ML | A1 | Voice agent, knowledge base, transcript pipeline |
| Voice Agents | AI/ML | A1 | Turtlemint voice agent |
| VAD | AI/ML | A1 | AshwaasAI data cleaning |
| Scikit-learn | AI/ML | A2 | No bullet |
| Pandas, NumPy | AI/ML | A2 | No bullet (implied by data cleaning) |
| Git | Tools | A2 | Implied (GitHub links) |
| Kubernetes (kubectl) | Tools | A1 | Live log tracing @ Turtlemint (**usage-level only**) |
| Kibana | Tools | A1 | Turtlemint |
| Selenium | Tools | A1 | AshwaasAI transcript pipeline |
| Claude Code | Tools | A1 | Turtlemint codebase analysis |
| DSA, OOP, DBMS, SDLC | CS Fundamentals | A2 | Coursework / LeetCode |

### 3.3 Tier A3 — earned but not listed (use these first)
These are already proven in the resume body. Adding them is **zero risk**.

| Skill / keyword | Proven by | Best for |
|---|---|---|
| Embeddings, Semantic Search | Document Assistant | AI/ML |
| Speech Recognition (ASR), Speech-to-Text | AshwaasAI Whisper | AI/ML |
| Fine-tuning, Hugging Face* | Whisper fine-tuning | AI/ML |
| NLP, Low-resource NLP | AshwaasAI | AI/ML |
| Prompt Engineering, LLM Guardrails | Voice agent SOP guardrails | AI/ML |
| Knowledge Base / Information Retrieval | Turtlemint KB, RAG | AI/ML |
| Data Cleaning / Preprocessing, Text Normalization | AshwaasAI audio + transcripts | AI/ML, Data |
| Real-time Inference | AshwaasAI live speech | AI/ML |
| Face Recognition | E-Bandobast | AI/ML, Mobile |
| Third-party API Integration | Insurer APIs @ Turtlemint, OpenRouteService | SDE, Full Stack |
| Authentication, Role-Based Access Control (RBAC) | Auth modules @ Freethink, role-based platform | SDE, Full Stack |
| Database Schema Design, Query Optimization | Freethink schema redesign | SDE, Full Stack |
| Production Debugging, Log Analysis | kubectl + Kibana @ Turtlemint | SDE |
| Business Rule / Validation Logic | Add-on eligibility rules, KYC validation | SDE |
| Real-time Systems, Push Notifications (FCM) | WebSockets, Firebase, FCM | Full Stack, Mobile |
| Firebase Cloud Messaging (FCM) | E-Bandobast | Full Stack, Mobile |
| Leaflet, OpenStreetMap, Geospatial / Maps | E-Bandobast zone mapping | Full Stack |
| Microservices (consumer-level)** | Debugging Spring Boot services on Kubernetes | SDE |
| Web Scraping / Automation | Selenium pipeline | AI/ML, SDE |

\* Hugging Face: Whisper fine-tuning almost certainly used HF `transformers`. **Candidate should confirm.**
\** Only phrase as "Microservices" if the JD asks. The candidate worked *in* a microservice setup, not designing one.

---

## 4. Role → skill graph (v0, LLM prior)

> ⚠️ v0 is built from general knowledge of fresher JDs in 2025–26, not counted from real data. Treat the frequency labels as estimates. Replace with corpus counts in v1 (Section 10).

Each Tier-B skill has: **frequency in fresher JDs** (High/Med/Low), **adjacency** (which A skill it hangs off), and **hours to basic working knowledge**.

### 4.1 AI/ML Engineer (fresher)
| Tier-B skill | Freq | Adjacent to | Hours |
|---|---|---|---|
| LangChain | High | RAG, LLMs | 3–4 |
| Vector Databases (FAISS / ChromaDB / pgvector / Pinecone) | High | RAG, Embeddings, Supabase (pgvector) | 2–3 |
| OpenAI API / LLM APIs | High | Gemini | 1–2 |
| Docker | High | Kubernetes usage | 3–4 |
| Hugging Face (if not confirmed A3) | High | Transformers, Whisper | 2–3 |
| LangGraph / AI Agents / Tool Calling | Med–High | Voice agent, LLMs | 3–4 |
| LlamaIndex | Med | RAG | 2–3 |
| TensorFlow / Keras | Med | PyTorch | 4–5 |
| RAG Evaluation (RAGAS) | Low–Med | RAG | 2–3 |
| MLflow / Experiment Tracking | Low–Med | Fine-tuning | 2–3 |
| Langfuse / LangSmith (LLM observability) | Low | LangChain | 1–2 |
| Streamlit / Gradio | Med | Python | 1–2 |
| Jupyter Notebook | Med | Python | 0 (just list it) |
| AWS basics (S3, EC2, SageMaker) | Med | — | 4–5 |

### 4.2 Software Engineer / SDE (fresher)
| Tier-B skill | Freq | Adjacent to | Hours |
|---|---|---|---|
| Docker | High | Kubernetes usage | 3–4 |
| Linux / Shell scripting | High | kubectl | 2–3 |
| PostgreSQL | High | MySQL, Supabase (is Postgres) | 1–2 |
| CI/CD (GitHub Actions) | Med–High | Git | 2–3 |
| Redis (caching) | Med | Backend | 2–3 |
| JWT / OAuth 2.0 | Med | Auth modules | 2 |
| Postman / Swagger (OpenAPI) | Med | REST APIs, FastAPI (auto-Swagger) | 1 |
| JUnit / PyTest (unit testing) | Med | Java, Python | 2–3 |
| Hibernate / JPA | Med (Java roles) | Spring Boot | 3–4 |
| AWS basics (EC2, S3, Lambda) | Med | — | 4–5 |
| Agile / Scrum | Med | SDLC | 0.5 |

### 4.3 Full Stack Developer (fresher)
| Tier-B skill | Freq | Adjacent to | Hours |
|---|---|---|---|
| TypeScript | High | JavaScript | 3–4 |
| Tailwind CSS | High | CSS | 1–2 |
| Redux / Zustand (state management) | Med–High | React | 2–3 |
| PostgreSQL | Med | MySQL, Supabase | 1–2 |
| Docker | Med | — | 3–4 |
| JWT / OAuth 2.0 | Med | Auth modules | 2 |
| Socket.IO | Med | WebSockets | 1 |
| Jest / React Testing Library | Med | JavaScript | 2–3 |
| Vercel / Netlify deployment | Med | Next.js | 1 |
| Mongoose | Med | MongoDB | 1 |
| GraphQL | Low–Med | REST APIs | 3–4 |
| Expo | Low–Med | React Native | 1 |

### 4.4 Tier C — never add
CUDA, Distributed Training, Reinforcement Learning, Kafka (internals), Spark/Hadoop, System Design (as a skill keyword), Rust, Go, Scala, Computer Vision research (YOLO training, etc.), Terraform, Kubernetes *administration* (Helm, cluster setup), Security certs, any skill whose JD line says "X years of experience in …".

---

## 5. Instructions for the editing LLM

**You are a resume skills-section editor.** You receive a JD, a role title, the chosen resume variant, and this file. You output a new TECHNICAL SKILLS section plus supporting notes. **You never touch any other part of the resume.**

### Step 1 — Extract JD keywords
- List every skill, tool, framework, language, platform and methodology in the JD, **in the JD's exact spelling** ("Node.js" not "NodeJS" if the JD says Node.js).
- Mark each one **Required** (must-have / requirements section) or **Preferred** (nice-to-have).
- Add **implied** keywords from Section 4 for this role: the top High-frequency items the JD didn't mention.

### Step 2 — Map each keyword to the skills DB
For each keyword, decide:
1. Already listed (A1/A2) → keep, adjust spelling to match the JD.
2. Synonym of a listed skill → add the JD's form alongside (e.g. JD says "Large Language Models" → write `LLMs (Large Language Models, Google Gemini)`).
3. In A3 (Section 3.3) → add it, no study needed.
4. In Tier B (Section 4) or clearly a ≤5 h tool next to an A skill → candidate for addition (max 4 total).
5. Tier C, or a heavy concept, or the JD demands years of experience in it → **do not add**. Report it under "Gaps not added".

### Step 3 — Choose additions
- Priority: **Required JD keywords** > **Preferred JD keywords** > **implied High-frequency** keywords.
- Add every A3 match first (free).
- Then up to **4 Tier-B** additions, ranked by: required in JD > high frequency > fewest hours to learn.

### Step 4 — Make room (keep the one-page layout)
- **Keep the same 7 lines** (category names may be renamed, see below). Each line ≤ ~150 characters, so it stays on one printed line.
- Total skills ≈ **40–48 items** across all lines. Don't bloat.
- Drop items in this order until it fits: irrelevant A2 skills (e.g. Vue.js, C for an AI role; VAD, Whisper fine-tuning for a pure Full Stack role) → irrelevant A1 skills → never drop anything the JD names.
- **Never drop** Python, Java, JavaScript, SQL, or anything the JD mentions.

### Step 5 — Order
- Category order: follow the variant (Section 2), but put the category holding the most **Required** JD keywords first.
- Within each line: JD Required keywords first, in JD order → Preferred → the rest.

### Step 6 — Rename categories when it helps
Allowed renames: `AI/ML` → `AI/ML & GenAI` or `Generative AI & LLMs` · `Tools & DevOps` → `DevOps & Cloud` / `Tools & Platforms` · `Backend` → `Backend & APIs` · `Frontend & Mobile` → `Frontend` (if mobile is irrelevant). Max 7 lines, no new line types beyond these.

### Step 7 — Formatting rules (ATS-safe)
- Plain text: `Category: item, item, item`. Comma-separated. No tables, icons, ratings, bars, or "proficiency levels".
- Use **both acronym and full form** for 1–3 key terms the JD uses (`RAG (Retrieval-Augmented Generation)`, `CI/CD`, `NLP`). Don't do it for every item.
- No duplicates across lines.
- Keep honest scope markers already in use, like `Kubernetes (kubectl)`. Never upgrade them (don't turn it into "Kubernetes").
- No soft skills in this section.

### Step 8 — Self-check before output
- [ ] Only the skills section changed
- [ ] ≤ 4 Tier-B additions, 0 Tier-C additions
- [ ] Every Required JD keyword is either present or listed under "Gaps not added" with a reason
- [ ] ≤ 7 lines, each ≤ ~150 chars, no duplicates
- [ ] Spelling matches the JD exactly

---

## 6. Output format (the editing LLM must return exactly this)

```
### 1. Variant used
<AI/ML | SDE | Full Stack> — <one-line reason>

### 2. New TECHNICAL SKILLS section (copy-paste ready)
<Category>: <items>
<Category>: <items>
...

### 3. Changelog
| Change | Skill | Tier | Reason |
|---|---|---|---|
| Added | ... | A3 / B | JD required / implied high-freq |
| Removed | ... | A2 | Irrelevant to role, space |
| Renamed | LLMs → LLMs (Large Language Models, Google Gemini) | — | JD phrasing |

### 4. JD coverage
- Required keywords: X / Y covered → missing: ...
- Preferred keywords: X / Y covered → missing: ...
- Gaps not added (Tier C or experience-gated): ... (reason)

### 5. Study sheet (one block per Tier-B addition)
#### <Skill> — ~<N> h
- **What it is (1 line):**
- **Why this JD wants it:**
- **How it connects to your existing work:** (e.g. "your Document Assistant RAG = what LangChain's RetrievalQA does")
- **Crash path:** 1) official quickstart (link name, not URL guess) 2) build: <a 1–3 h mini task on an existing project> 3) read: <key concept>
- **5 likely interview questions:**
  1. ...
- **One-liner to say in the interview:** "I've used X to …"
```

---

## 7. Worked example (short)

**Input:** Role "AI Engineer – Fresher". JD Required: Python, LLMs, RAG, LangChain, vector databases, REST APIs, Docker. Preferred: Hugging Face, AWS.

**Variant:** AI/ML.

**Output skills section:**
```
AI/ML & GenAI: LLMs (Large Language Models, Google Gemini), RAG (Retrieval-Augmented Generation), LangChain, Vector Databases (FAISS, pgvector), Embeddings, Semantic Search, Hugging Face, Transformers, PyTorch, Whisper Fine-tuning, Speech Recognition (ASR), Voice Agents, Prompt Engineering
Languages: Python, Java, JavaScript, SQL, C++
Backend & APIs: REST APIs, FastAPI, Node.js, Express, Java Spring Boot, WebSockets
Databases: MySQL, MongoDB, Supabase, Firebase Realtime DB
Data & ML Libraries: Pandas, NumPy, Scikit-learn
DevOps & Cloud: Docker, Git, Kubernetes (kubectl), Kibana, Selenium, Claude Code
CS Fundamentals: Data Structures & Algorithms, OOP, DBMS, SDLC
```
*(Frontend line dropped for space on an AI role; React/Next.js are still visible in the project bullets. "Data & ML Libraries" replaces the frontend line, which keeps the count at 7.)*

**Tier-B added (3):** LangChain, Vector Databases (FAISS), Docker → 3 study sheets.
**A3 added (free):** Embeddings, Semantic Search, Speech Recognition (ASR), Prompt Engineering, Hugging Face (if confirmed), pgvector (via Supabase, if confirmed).
**Removed:** C, Vue.js, VAD, HTML/CSS, React, Next.js, React Native (irrelevant to this JD).
**Gaps not added:** AWS (Preferred; 4–5 h, so it's left out to stay within the 4-addition cap. The candidate can choose to swap it in).

---

## 8. Prompt template (paste into the other LLM)

```
You are my resume skills-section editor. Follow the attached "Resume Skills Crafter" file exactly,
especially Sections 5–7. Edit ONLY the TECHNICAL SKILLS section. Return output in the Section 6 format.

ROLE TITLE: <paste>
RESUME VARIANT: <AI/ML | SDE | Full Stack | "you choose">
JD:
<paste full JD>

Extra constraints for this application (optional): <e.g. "max 2 Tier-B adds", "I already know Docker">
```

Tip: when you learn a Tier-B skill (or confirm an A3 item like Hugging Face), **update Section 3** so the skill moves to A1/A3 and the next application treats it as safe.

---

## 9. Candidate's checklist per application
1. Pick the variant (Section 2).
2. Paste the template (Section 8) + JD into the editing LLM.
3. Review the changelog. Reject any addition you don't want to study.
4. Paste the new skills section into the resume source (Word/Docs/LaTeX), export PDF.
5. **Parse check:** open the PDF, Ctrl+A → copy → paste into a plain text editor. Every skill should come out readable and on its line. (Or run `pdftotext -layout resume.pdf -`.)
6. Save as `Kavish_Toraskar_<Company>_<Role>.pdf`. Log it (Section 10.2).
7. If shortlisted → do the study sheets **before** the interview.

---

## 10. Roadmap

### 10.1 v1 — real skill graph
- Collect 300–1000 fresher JDs per role family from public datasets (Kaggle job postings) or the Adzuna API. Avoid scraping LinkedIn/Naukri (ToS).
- LLM-extract skills per JD → normalize names (e.g. "NodeJS" = "Node.js") against a taxonomy (Lightcast Open Skills / ESCO).
- Compute `P(skill | role)` (frequency) and lift/PMI between skill pairs (`P(B | A in JD)`). Replace the Freq column in Section 4 with real numbers.

### 10.2 Feedback loop
Track every application:
| Date | Company | Role | Variant | Tier-B added | Match score | Shortlisted? |
|---|---|---|---|---|---|---|

After about 30 applications, compare shortlist rates by variant and by additions. This is the only way to know whether the system works.

### 10.3 v2 — automation (optional)
Python + LLM API + Streamlit: upload JD → auto-select variant → generate the Section 6 output → render PDF → auto parse check → keyword + embedding match score.
