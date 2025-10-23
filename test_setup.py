#!/usr/bin/env python3
"""Test script to verify Voyager setup."""

import os
import sys

from dotenv import load_dotenv


def test_env_variables():
    """Test that environment variables are set."""
    print("Testing environment variables...")

    load_dotenv()

    required = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]

    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False

    print("✓ Environment variables configured")
    return True


def test_postgres():
    """Test PostgreSQL connection."""
    print("\nTesting PostgreSQL connection...")

    try:
        import psycopg2

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "voyager_db"),
            user=os.getenv("POSTGRES_USER", "voyager"),
            password=os.getenv("POSTGRES_PASSWORD", "voyager_pass"),
        )
        conn.close()
        print("✓ PostgreSQL connection successful")
        return True

    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("   Make sure docker-compose is running: docker-compose up -d")
        return False


def test_chromadb():
    """Test ChromaDB connection."""
    print("\nTesting ChromaDB connection...")

    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", "8000")),
            settings=Settings(anonymized_telemetry=False),
        )

        # Test heartbeat
        client.heartbeat()
        print("✓ ChromaDB connection successful")
        return True

    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        print("   Make sure docker-compose is running: docker-compose up -d")
        return False


def test_azure_openai():
    """Test Azure OpenAI connection."""
    print("\nTesting Azure OpenAI connection...")

    try:
        from langchain_openai import AzureChatOpenAI

        llm = AzureChatOpenAI(
            model="gpt-5-nano",
            api_version="2025-04-01-preview",
            temperature=0,
        )

        # Try a simple call
        response = llm.invoke("Say 'test' and nothing else")
        print("✓ Azure OpenAI connection successful")
        print(f"  Response: {response.content[:50]}...")
        return True

    except Exception as e:
        print(f"❌ Azure OpenAI connection failed: {e}")
        print("   Check your API key and endpoint in .env")
        return False


def test_node_dependencies():
    """Test Node.js dependencies."""
    print("\nTesting Node.js dependencies...")

    try:
        import subprocess

        result = subprocess.run(
            ["node", "-e", "require('mineflayer'); console.log('ok')"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            print("✓ Node.js dependencies installed")
            return True
        else:
            print("❌ Node.js dependencies missing")
            print("   Run: npm install")
            return False

    except Exception as e:
        print(f"❌ Node.js test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Voyager Minecraft AI - Setup Test")
    print("=" * 60)

    tests = [
        test_env_variables,
        test_postgres,
        test_chromadb,
        test_node_dependencies,
        test_azure_openai,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✓ All tests passed! You're ready to run Voyager.")
        print("\nNext steps:")
        print("  1. Activate venv: source venv/bin/activate")
        print("  2. Run: python src/main.py")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
