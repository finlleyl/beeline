from fastapi import APIRouter, Query
import tempfile
import subprocess
import os
import json
from fastapi.responses import FileResponse

from neo4j import GraphDatabase

router = APIRouter(prefix="/components", tags=["components"])


@router.get("")
async def get_visualizatioin():
    return True


@router.post("/analyse")
async def analyse_repo(git_url: str = Query(..., description="GitHub repo URL")):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "repo")
    
        print("Cloning repo...")
        clone_result = subprocess.run(
            ["git", "clone", git_url, repo_path],
            capture_output=True, text=True
        )
        print(clone_result.stderr)
        if clone_result.returncode != 0:
            return {"error": "Failed to clone repo", "details": clone_result.stderr}
        
        print("Importing repo into Neo4j...")
        # First, parse the code
        parse_result = subprocess.run(
            ["joern-parse", repo_path],
            capture_output=True, text=True
        )
        print(parse_result.stderr)
        if parse_result.returncode != 0:
            return {"error": "Joern parse failed", "details": parse_result.stderr}
        
        # Then, import into Neo4j
        import_result = subprocess.run(
            ["joern", "import", repo_path],
            capture_output=True, text=True
        )
        print(import_result.stderr)
        if import_result.returncode != 0:
            return {"error": "Joern import failed", "details": import_result.stderr}
        
        # Verify data was imported by checking Neo4j
        try:
            driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
            with driver.session() as session:
                # Check if any nodes were created
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                if count == 0:
                    return {"error": "No data was imported into Neo4j"}
                
                return {
                    "status": "success", 
                    "project_path": repo_path,
                    "nodes_imported": count
                }
        except Exception as e:
            return {"error": "Failed to verify Neo4j import", "details": str(e)}


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


@router.post("/export")
async def export_data(project_path: str = Query(..., description="Path to the project to export")):
    """Export data using Joern export command"""
    try:
        # Run joern-export command
        joern_result = subprocess.run(
            ["joern-export", "--out", "export.json", project_path],
            capture_output=True, text=True
        )
        
        if joern_result.returncode != 0:
            return {"error": "Joern export failed", "details": joern_result.stderr}
        
        # Check if export file exists
        export_file = "export.json"
        if not os.path.exists(export_file):
            return {"error": "Export file not found"}
            
        return FileResponse(
            export_file,
            media_type="application/json",
            filename="joern_export.json"
        )
    except Exception as e:
        return {"error": "Export failed", "details": str(e)}


@router.post("/export-neo4j")
async def export_neo4j(query: str = Query(..., description="Cypher query to export data from Neo4j")):
    """Export data from Neo4j to a file"""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        
        def run_query(tx):
            result = tx.run(query)
            return [dict(record) for record in result]
        
        with driver.session() as session:
            records = session.read_transaction(run_query)
            
            # Save results to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                json.dump(records, tmp, indent=2)
                tmp_path = tmp.name
            
            return FileResponse(
                tmp_path,
                media_type="application/json",
                filename="neo4j_export.json"
            )
    except Exception as e:
        return {"error": "Neo4j export failed", "details": str(e)}
