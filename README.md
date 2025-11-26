### Travel-agent
    LangGraph + Hierarchical Agent + FastAPI + SSE + VUE3
    top supervisor(parallel run) ---> final plan
      -> hotel team
        -> searcher -> evaluator
      -> itinerary team
    
    
[![Demo video]()](https://github.com/thatqhu/travel-agent/raw/refs/heads/main/assets/travel_agent.mp4)

##### How to use
    docker-compose up -d
    docker exec -it travel_frontend sh
    cd /app && npm install && npm run dev
    docker exec -it travel_frontend sh
    cd /app && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
##### How to development
    open vscode -> `attach to running container`
    
