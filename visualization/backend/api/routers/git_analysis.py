from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from visualization.backend.services import gitmodule
from llm.generate import generate_answer_for_git
import os

router = APIRouter(
    prefix="/git-analysis",
    tags=["git-analysis"]
)

class FunctionAnalysisRequest(BaseModel):
    file_path: str
    start_line: int
    end_line: int

class FunctionAnalysisResponse(BaseModel):
    commits: List[dict]
    coupling: List[dict]
    llm_prompt: str

@router.post("/analyze-function")
async def analyze_function(request: FunctionAnalysisRequest):
    try:
        # Get repository path (assuming the file is in the workspace)
        repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(request.file_path))))
        
        # Get repository
        repo = gitmodule.get_repo(repo_path)
        
        # Get relative file path
        relative_file_path = os.path.relpath(request.file_path, repo_path)
        
        # Get commit IDs for the specified lines
        commit_ids = gitmodule.get_commit_ids_for_lines(
            repo,
            relative_file_path,
            request.start_line,
            request.end_line
        )
        
        if not commit_ids:
            raise HTTPException(status_code=404, detail="No commits found for the specified function lines")
        
        # Get commit metadata
        commits_meta = gitmodule.get_information_for_commits(repo, commit_ids)
        
        # Compute coupling
        coupling = gitmodule.compute_coupling(
            commits_meta,
            relative_file_path,
            top_n=10
        )
        
        # Build LLM prompt
        target = {
            "file": relative_file_path,
            "start": request.start_line,
            "end": request.end_line
        }
        
        llm_prompt = gitmodule.build_llm_prompt(
            target,
            commits_meta,
            coupling,
            max_commits=3,
            max_coupled=10,
            max_recommendations=5
        )
        
        return generate_answer_for_git(llm_prompt)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 