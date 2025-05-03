from fastapi import APIRouter, Query
import tempfile
import subprocess
import os
from neo4j import GraphDatabase

router = APIRouter(prefix="/components", tags=["components"])


@router.get("")
async def get_visualizatioin():
    return True


@router.post("/analyse")
async def analyse_repo(git_url: str = Query(..., description="GitHub repo URL")):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "repo")
        clone_result = subprocess.run(
            ["git", "clone", git_url, repo_path],
            capture_output=True, text=True
        )
        if clone_result.returncode != 0:
            return {"error": "Failed to clone repo", "details": clone_result.stderr}
        
        joern_result = subprocess.run(
            ["joern-import", repo_path],
            capture_output=True, text=True
        )
        if joern_result.returncode != 0:
            return {"error": "Joern failed", "details": joern_result.stderr}
        
        return {"status": "success", "project_path": repo_path}


@router.post("/query")
async def query_graph(query: str = Query(..., description="Cypher query to execute on the Neo4j database")):
    # Assuming Neo4j is running on localhost:7687 with default credentials
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    
    def run_query(tx):
        result = tx.run(query)
        return [record for record in result]
    
    with driver.session() as session:
        records = session.read_transaction(run_query)
        return {"result": records}
