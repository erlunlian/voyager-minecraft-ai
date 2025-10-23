"""Main entry point for Voyager Minecraft AI."""

import os
import sys
import traceback

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.action import ActionAgent
from agents.critic import CriticAgent
from agents.curriculum import CurriculumAgent
from config import Config
from graph.voyager_graph import VoyagerGraph
from minecraft.executor import MinecraftExecutor
from session.manager import SessionManager
from skills.primitives import load_primitive_skills
from skills.skill_manager import SkillManager


def print_header():
    """Print startup header."""
    print("=" * 60)
    print("VOYAGER MINECRAFT AI")
    print("=" * 60)


def initialize_session(config: Config) -> SessionManager:
    """Initialize or resume session."""
    print("- Session Manager")
    session_manager = SessionManager(config.get_db_url())

    active_session = session_manager.get_active_session(
        config.minecraft_config["username"]
    )

    if active_session:
        print(f"  Found active session ID: {active_session}")
        response = input("  Resume this session? (y/n): ").strip().lower()

        if response == "y":
            session_manager.resume_session(active_session)
            print(f"  Resumed session {active_session}")
        else:
            # Close old session and create new one
            session_manager.update_session_status(active_session, "closed")
            session_manager.create_session(
                config.minecraft_config["username"], config.minecraft_config["host"]
            )
    else:
        # Create new session
        session_manager.create_session(
            config.minecraft_config["username"], config.minecraft_config["host"]
        )

    return session_manager


def initialize_skill_manager(config: Config) -> SkillManager:
    """Initialize skill manager and load primitive skills if needed."""
    print("- Skill Manager (ChromaDB)")
    skill_manager = SkillManager(
        chroma_host=config.chroma_host,
        chroma_port=config.chroma_port,
        azure_api_key=config.azure_api_key,
        azure_endpoint=config.azure_endpoint,
    )

    if skill_manager.get_count() == 0:
        print("  Loading primitive skills...")
        load_primitive_skills(skill_manager)
    else:
        print(f"  Loaded existing library ({skill_manager.get_count()} skills)")

    return skill_manager


def initialize_agents(config: Config):
    """Initialize all agents."""
    print("- Curriculum Agent")
    curriculum_agent = CurriculumAgent(config.azure_api_key, config.azure_endpoint)

    print("- Action Agent")
    action_agent = ActionAgent(config.azure_api_key, config.azure_endpoint)

    print("- Critic Agent")
    critic_agent = CriticAgent(config.azure_api_key, config.azure_endpoint)

    return curriculum_agent, action_agent, critic_agent


def initialize_minecraft_executor(config: Config) -> MinecraftExecutor:
    """Initialize and connect Minecraft executor."""
    print("- Minecraft Executor")
    executor = MinecraftExecutor(config.minecraft_config)
    executor.start()

    print(
        f"\nConnecting to Minecraft server at {config.minecraft_config['host']}:{config.minecraft_config['port']}..."
    )

    try:
        executor.connect(
            host=config.minecraft_config["host"],
            port=config.minecraft_config["port"],
            username=config.minecraft_config["username"],
        )
        print("✓ Connected to Minecraft")
        return executor
    except Exception as e:
        print(f"✗ Failed to connect to Minecraft: {e}")
        print("\nMake sure:")
        print("  1. Minecraft server is running")
        print("  2. Server address is correct in .env")
        print("  3. Server is accessible")
        raise


def cleanup(executor: MinecraftExecutor, session_manager: SessionManager):
    """Cleanup resources."""
    print("\nCleaning up...")
    executor.disconnect()
    if session_manager.current_session_id:
        session_manager.update_session_status(
            session_manager.current_session_id, "paused"
        )
    session_manager.close()
    print("Done.")


def main():
    """Initialize and run Voyager agent."""
    print_header()

    try:
        # Load configuration
        config = Config()

        print("\nInitializing components...")

        # Initialize all components
        session_manager = initialize_session(config)
        skill_manager = initialize_skill_manager(config)
        curriculum_agent, action_agent, critic_agent = initialize_agents(config)
        executor = initialize_minecraft_executor(config)

        # Initialize Voyager state machine
        print("\n- Voyager State Machine")
        voyager = VoyagerGraph(
            curriculum_agent=curriculum_agent,
            action_agent=action_agent,
            critic_agent=critic_agent,
            skill_manager=skill_manager,
            executor=executor,
            session_manager=session_manager,
            db_config=config.db_config,
        )

        print("\n" + "=" * 60)
        print("Voyager agent initialized successfully!")
        print("=" * 60)

        # Run the agent
        print("\nStarting agent loop...\n")

        try:
            voyager.run()
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        except Exception as e:
            print(f"\n\nError during execution: {e}")
            traceback.print_exc()
        finally:
            cleanup(executor, session_manager)

    except ValueError as e:
        print(f"\nConfiguration error: {e}")
    except Exception as e:
        print(f"\nFailed to initialize: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
