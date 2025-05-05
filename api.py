from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import gitmodule
import os

app = FastAPI(title="Git Analysis API")

class FileAnalysisRequest(BaseModel):
    repo_path: str
    file_path: str
    start_line: int
    end_line: int
    max_commits: int = 3
    max_coupled: int = 10
    max_recommendations: int = 5

class FileAnalysisResponse(BaseModel):
    commits: List[dict]
    coupling: List[dict]
    llm_prompt: str

@app.post("/analyze", response_model=FileAnalysisResponse)
async def analyze_file(request: FileAnalysisRequest):
    try:
        # Get repository
        repo = gitmodule.get_repo(request.repo_path)
        
        # Get commit IDs for the specified lines
        commit_ids = gitmodule.get_commit_ids_for_lines(
            repo,
            request.file_path,
            request.start_line,
            request.end_line
        )
        
        if not commit_ids:
            raise HTTPException(status_code=404, detail="No commits found for the specified lines")
        
        # Get commit metadata
        commits_meta = gitmodule.get_information_for_commits(repo, commit_ids)
        
        # Compute coupling
        coupling = gitmodule.compute_coupling(
            commits_meta,
            request.file_path,
            top_n=request.max_coupled
        )
        
        # Build LLM prompt
        target = {
            "file": request.file_path,
            "start": request.start_line,
            "end": request.end_line
        }
        
        llm_prompt = gitmodule.build_llm_prompt(
            target,
            commits_meta,
            coupling,
            max_commits=request.max_commits,
            max_coupled=request.max_coupled,
            max_recommendations=request.max_recommendations
        )
        
        return FileAnalysisResponse(
            commits=commits_meta,
            coupling=coupling,
            llm_prompt=llm_prompt
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 