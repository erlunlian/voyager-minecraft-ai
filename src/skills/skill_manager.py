import json
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from langchain_openai import AzureOpenAIEmbeddings

from models import Skill


class SkillManager:
    """Manages skills using ChromaDB for semantic search."""

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        azure_api_key: str = None,
        azure_endpoint: str = None,
    ):
        """Initialize skill manager with ChromaDB client."""

        # Connect to ChromaDB
        self.client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )

        # Initialize Azure embeddings
        self.embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-ada-002",
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version="2025-04-01-preview",
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(name="minecraft_skills")
        except Exception:
            self.collection = self.client.create_collection(
                name="minecraft_skills",
                metadata={"description": "Minecraft bot skills library"},
            )

        print(
            f"Skill Manager initialized. Skills in library: {self.collection.count()}"
        )

    def add_skill(
        self,
        name: str,
        description: str,
        code: str,
        parameters: List[str] = None,
        tags: List[str] = None,
    ) -> str:
        """Add a new skill to the library."""

        skill_id = f"skill_{name}_{self.collection.count()}"

        # Generate embedding for skill description
        embedding = self.embeddings.embed_query(description)

        metadata = {
            "name": name,
            "description": description,
            "parameters": json.dumps(parameters or []),
            "tags": json.dumps(tags or []),
        }

        # Add to ChromaDB
        self.collection.add(
            ids=[skill_id],
            embeddings=[embedding],
            documents=[code],
            metadatas=[metadata],
        )

        print(f"Added skill: {name}")
        return skill_id

    def retrieve_skills(self, query: str, n_results: int = 5) -> List[Skill]:
        """Retrieve relevant skills based on semantic search."""

        if self.collection.count() == 0:
            return []

        # Generate embedding for query
        query_embedding = self.embeddings.embed_query(query)

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
        )

        skills = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                skill = Skill(
                    id=results["ids"][0][i],
                    name=results["metadatas"][0][i]["name"],
                    description=results["metadatas"][0][i]["description"],
                    code=results["documents"][0][i],
                    parameters=json.loads(results["metadatas"][0][i]["parameters"]),
                    tags=json.loads(results["metadatas"][0][i]["tags"]),
                    distance=(
                        results["distances"][0][i] if "distances" in results else None
                    ),
                )
                skills.append(skill)

        return skills

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get a specific skill by name."""

        results = self.collection.get(where={"name": name})

        if results["ids"]:
            return Skill(
                id=results["ids"][0],
                name=results["metadatas"][0]["name"],
                description=results["metadatas"][0]["description"],
                code=results["documents"][0],
                parameters=json.loads(results["metadatas"][0]["parameters"]),
                tags=json.loads(results["metadatas"][0]["tags"]),
            )
        return None

    def update_skill(
        self,
        skill_id: str,
        code: str = None,
        description: str = None,
        tags: List[str] = None,
    ):
        """Update an existing skill."""

        # Get current skill
        current = self.collection.get(ids=[skill_id])
        if not current["ids"]:
            raise ValueError(f"Skill not found: {skill_id}")

        metadata = current["metadatas"][0]
        document = current["documents"][0]

        # Update fields
        if code:
            document = code
        if description:
            metadata["description"] = description
        if tags:
            metadata["tags"] = json.dumps(tags)

        # Regenerate embedding if description changed
        if description:
            embedding = self.embeddings.embed_query(description)
        else:
            embedding = None

        # Update in ChromaDB
        update_kwargs = {
            "ids": [skill_id],
            "documents": [document],
            "metadatas": [metadata],
        }
        if embedding:
            update_kwargs["embeddings"] = [embedding]

        self.collection.update(**update_kwargs)

    def delete_skill(self, skill_id: str):
        """Delete a skill from the library."""
        self.collection.delete(ids=[skill_id])

    def list_all_skills(self) -> List[Skill]:
        """List all skills in the library."""

        if self.collection.count() == 0:
            return []

        results = self.collection.get()

        skills = []
        for i in range(len(results["ids"])):
            skill = Skill(
                id=results["ids"][i],
                name=results["metadatas"][i]["name"],
                description=results["metadatas"][i]["description"],
                code=results["documents"][i],
                parameters=json.loads(results["metadatas"][i]["parameters"]),
                tags=json.loads(results["metadatas"][i]["tags"]),
            )
            skills.append(skill)

        return skills

    def get_count(self) -> int:
        """Get total number of skills."""
        return self.collection.count()
