# AI-Powered Water Supply & Distribution Process Explainer Bot
### Generative AI for Public Awareness and Sustainable Water Utilities

**Project 26 | Industry Domain: Water Utilities / Municipal Services**

**Developed by:**
1. Katakam Sahithi Rithvika
2. Sai Spoorthy Eturu
3. Kommera Harihansika

**Institution:** BVRIT Hyderabad College of Engineering for Women

---

## Abstract

Water supply departments frequently receive queries from citizens regarding water treatment, distribution processes, pressure issues, water safety and conservation practices. Technical explanations can be difficult for the general public to understand, resulting in repetitive queries and increased workload for municipal customer support teams.

This project adapts an existing AI-driven Smart Water Management prototype into a **Generative AI-based Water Supply & Distribution Process Explainer Bot**. The system uses Google's Gemini Flash models to provide simple, clear and accessible explanations of water supply and distribution processes through an interactive Streamlit web application.

The chatbot explains the stages of water treatment, the functioning of distribution networks, common causes of water pressure variations, and general water conservation guidelines. It is designed to improve public awareness and help citizens understand water-related processes without requiring technical expertise.

The system follows an explanation-only approach. It does not register complaints, submit service requests, schedule water supply, predict supply timings or perform operational actions. A carefully designed system prompt helps keep responses within the intended informational scope.

The project demonstrates the responsible application of Generative AI in municipal services, supporting public education, transparency and sustainable water awareness.

## 1. Problem Statement

Water utilities and municipal departments handle numerous citizen queries concerning water distribution schedules, pressure issues, treatment processes and water safety guidelines. Technical information is often difficult for citizens to interpret, while customer service teams spend considerable time answering repetitive informational questions.

An AI-based explanation system is therefore needed to make water-related processes easier to understand and improve public awareness.

The proposed solution is a conversational chatbot that provides accessible explanations of water supply and distribution processes while maintaining clear boundaries around its capabilities.

## 2. Project Objectives

- Explain water treatment and distribution processes in simple language.
- Improve public understanding of water utilities and municipal services.
- Provide general information about common water pressure issues.
- Promote water conservation and responsible usage.
- Reduce repetitive informational queries through self-service explanations.
- Integrate Google Gemini Flash models into a Python-based application.
- Develop an accessible web interface using Streamlit.
- Implement system-level restrictions to prevent unauthorised actions and unsupported predictions.
- Demonstrate responsible and purpose-specific use of Generative AI.

## 3. Proposed Solution

The existing Smart Water Management prototype is being adapted to focus on citizen education and process explanation rather than operational monitoring and prediction.

The revised application introduces a conversational interface through which users can ask questions about water supply and distribution. Gemini Flash generates easy-to-understand responses based on the user's query and the application's system instructions.

The chatbot focuses on explaining how water systems work, what common water-related terms mean, and which general conservation practices citizens can follow.

The existing prototype's reusable application components and relevant water-related resources may be retained where appropriate. The final application's primary functionality will be the explanation-only chatbot.

## 4. Key Features

### 4.1 Water Treatment Explanation
Explains the general stages involved in treating water, including screening, sedimentation, filtration and disinfection, where applicable to the treatment process being discussed.

### 4.2 Water Distribution Process
Describes how treated water can move through storage facilities, pumping infrastructure and distribution pipelines to reach consumers.

### 4.3 Water Pressure Awareness
Explains common factors that can affect water pressure, such as elevation, demand, pipe restrictions and pumping conditions, without claiming to diagnose a specific network.

### 4.4 Water Conservation Guidance
Provides general educational information about reducing water wastage, identifying avoidable water use and adopting responsible water consumption practices.

### 4.5 Gemini Flash Integration
Uses Google's Gemini Flash models to generate conversational, context-aware explanations through the Google AI Studio API.

### 4.6 Interactive Streamlit Interface
Provides a simple web interface where citizens can enter questions and receive readable explanations.

### 4.7 Responsible AI Guardrails
Uses system instructions to keep the chatbot within its intended informational scope and discourage unsupported, unrelated or action-oriented responses.

### 4.8 Citizen-Friendly Responses
Presents technical concepts in straightforward language suitable for users without specialised knowledge of water infrastructure.

## 5. System Scope and Limitations

The chatbot is intended exclusively for informational and educational purposes.

**Supported functionality**
- Explaining water treatment processes.
- Describing water distribution systems.
- Explaining common causes of water pressure variations.
- Sharing general water conservation guidelines.
- Clarifying water utility terminology.

**Out of scope**
- Registering complaints or service requests.
- Booking appointments or scheduling water supply.
- Predicting the date or time of water availability in a particular area.
- Controlling pumps, valves or other physical infrastructure.
- Diagnosing actual municipal network faults.
- Providing verified local supply schedules without an authorised data source.
- Making unsupported claims about drinking-water safety or water quality.

When asked to perform an out-of-scope action, the chatbot should politely explain its limitation and direct the user to the relevant official water authority where appropriate.

## 6. System Architecture

The proposed application follows a simple conversational AI architecture.

1. **User Interface Layer:** Streamlit accepts user questions and displays responses.
2. **Application Layer:** Python handles input processing, conversation flow and API communication.
3. **Generative AI Layer:** Google Gemini Flash generates explanations based on the user's question and the configured system instructions.
4. **Safety and Response Layer:** The application applies scope restrictions and handles invalid inputs, API failures and unsuitable requests before presenting the response.

### Workflow

User Query → Streamlit Interface → Python Application → Scope and Safety Instructions → Gemini Flash API → Response Handling → Explanation Displayed to User

The original prototype's backend, sensor simulator, databases and monitoring components may remain available as supporting components if needed. They are not the core functionality of the revised explainer bot.

## 7. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Generative AI | Google Gemini Flash models |
| AI API | Google AI Studio API |
| Web Framework | Streamlit |
| API Integration | Google GenAI SDK, if used in the implementation |
| Version Control | Git and GitHub |
| Deployment | Existing prototype deployment, subject to integration and testing |

The existing prototype also documents technologies such as FastAPI, SQLite, PostgreSQL, sensor simulation, PyTorch, TensorFlow and Plotly. These belong to the original smart water management system and should be retained in the active technology list only where they remain relevant to the final implementation.

## 8. Sample Queries and Expected Behaviour

| Sample Query | Expected Behaviour |
|---|---|
| Explain the water treatment process. | Describes the general stages of water treatment in simple language. |
| How does water distribution work? | Explains storage, pumping and pipeline distribution. |
| What are some water conservation tips? | Provides general water-saving practices. |
| Explain common water pressure issues. | Describes possible causes without diagnosing a specific network. |
| When will water supply arrive in my area? | Clarifies that the chatbot cannot predict local supply timings and suggests checking official municipal updates. |
| Register a complaint about low water pressure. | Explains that the chatbot cannot register complaints and directs the user to the appropriate official channel. |
| Is the water in my area safe to drink? | Explains that actual safety cannot be established from the chatbot alone and recommends consulting official water-quality information or the relevant authority. |

These queries will be used to evaluate the chatbot's clarity, relevance and compliance with its informational limitations.

## 9. Responsible Generative AI

Responsible AI is a central design principle of the project.

- **Purpose limitation:** Responses are restricted to water-related explanations and general educational information.
- **No unauthorised actions:** The chatbot cannot register complaints, schedule services or control infrastructure.
- **No supply predictions:** The chatbot must not invent or forecast local water supply timings.
- **Grounded communication:** The system should avoid presenting uncertain explanations as confirmed facts.
- **User awareness:** Users should be reminded that the chatbot provides general information rather than official municipal announcements.
- **Error handling:** API failures, empty queries and unsupported requests should be handled gracefully.
- **Credential security:** API keys must be stored securely and must not be committed to the public repository.

System prompts help establish these boundaries, but prompts alone cannot guarantee perfect compliance. The implementation should also validate inputs and test responses against prohibited requests.

## 10. Quick Start Guide

### Prerequisites

- Python 3.8 or higher, subject to the requirements of the selected Gemini SDK.
- pip package manager.
- Git.
- A Google AI Studio API key.
- The dependencies listed in `requirements.txt`.

### Installation

Clone the existing repository:

```bash
git clone https://github.com/ESpoorthy/ai-smart-water-management-iot.git
cd ai-smart-water-management-iot
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

Configure the Gemini API key using an environment variable or Streamlit secrets, depending on the application's implementation.

For a local environment variable in Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="your_api_key"
```

Replace `your_api_key` with your own key. Do not commit the key to GitHub.

### Run the Application

The original prototype documents the following Streamlit entry point:

```bash
streamlit run dashboard/streamlit_app.py
```

This command runs the existing dashboard. The chatbot will be available through this command only after its integration into the appropriate application entry point.

Open the local Streamlit URL shown in the terminal, typically `http://localhost:8501`.

**Note:** The existing prototype also documents a FastAPI backend and sensor simulator. Those components are required only if the retained application features depend on them. The revised chatbot should be runnable without unnecessary operational services wherever possible.

## 11. Existing Prototype and Deployment

**Original repository:**  
https://github.com/ESpoorthy/ai-smart-water-management-iot

**Existing prototype deployment:**  
https://ai-smart-water-management-iot.onrender.com

The repository and deployment belong to the original AI-driven Smart Water Management prototype. The chatbot integration, interface changes and scope restrictions must be tested before the deployment is presented as the completed Project 26 application.

## 12. Project Structure

The existing prototype documents the following structure. The actual structure may evolve as the explainer bot is integrated.

```text
smart_water_system/
│
├── backend/
│   └── fastapi_server.py
│
├── ai_models/
│   ├── anomaly_detection.py
│   └── lstm_forecast.py
│
├── dashboard/
│   └── streamlit_app.py
│
├── simulator/
│   └── sensor_simulator.py
│
├── hardware/
│   └── esp32_example.ino
│
├── database/
│   └── water.db
│
├── requirements.txt
├── test_system.py
├── config.example.py
└── run_system.sh
```

The chatbot integration may introduce additional modules for Gemini API communication, prompt configuration, response validation and chatbot testing. The final directory structure should reflect the actual committed implementation rather than planned files that do not yet exist.

## 13. Testing and Validation

The revised application will be tested using representative water utility questions and requests that fall outside its scope.

Testing will focus on:

- Correctness and clarity of water-process explanations.
- Relevance of answers to user questions.
- Handling of common water pressure queries.
- Quality of general conservation guidance.
- Rejection of complaint registration and scheduling requests.
- Prevention of local supply-time predictions.
- Handling of API errors and invalid inputs.
- Secure handling of API credentials.
- Usability of the Streamlit interface.

The system should be considered ready for demonstration only after these checks have been completed. Performance metrics or accuracy figures will be reported only if they are supported by actual testing.

## 14. Expected Outcomes

The intended outcomes of the project are:

- Improved citizen understanding of water supply and distribution processes.
- Easier access to simple, water-related educational information.
- Reduced dependence on support staff for repetitive informational explanations.
- A user-friendly demonstration of Generative AI in municipal services.
- Clear separation between informational assistance and operational water utility functions.
- Increased awareness of responsible water conservation practices.

These are project objectives; measurable improvements in helpline workload or public awareness would require separate evaluation.

## 15. Future Enhancements

Potential future enhancements, subject to the project's informational scope, include:

- Multilingual explanations for a wider range of citizens.
- Voice-based questions and spoken explanations.
- Illustrated water treatment and distribution workflows.
- Curated, authoritative educational content.
- Improved accessibility and mobile-friendly interface design.
- A broader test suite for safety, reliability and response quality.

Any future integration with official municipal data should preserve the prohibition on supply-time predictions, complaint registration and unauthorised service actions.

## 16. References

- Google AI for Developers — Gemini API documentation: https://ai.google.dev/gemini-api/docs
- Streamlit Documentation: https://docs.streamlit.io/
- United Nations Sustainable Development Goal 6 — Clean Water and Sanitation: https://sdgs.un.org/goals/goal6
- Existing Smart Water Management prototype: https://github.com/ESpoorthy/ai-smart-water-management-iot

## 17. Team

**Project Team — BVRIT Hyderabad College of Engineering for Women**

- Katakam Sahithi Rithvika
- Sai Spoorthy Eturu
- Kommera Harihansika

**Project:** Water Supply & Distribution Process Explainer Bot  
**Domain:** Water Utilities / Municipal Services  
**Core Technologies:** Python, Streamlit, Google AI Studio API and Gemini Flash models

---

*An educational Generative AI solution for clearer water utility communication and responsible public awareness.*
