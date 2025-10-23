"""Voyager LangGraph State Machine."""

import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph

from graph.types import VoyagerState
from models import BotState, ExecutionResult


class VoyagerGraph:
    """LangGraph state machine for Voyager agent."""

    def __init__(
        self,
        curriculum_agent,
        action_agent,
        critic_agent,
        skill_manager,
        executor,
        session_manager,
        db_config: Dict[str, str],
    ):

        self.curriculum_agent = curriculum_agent
        self.action_agent = action_agent
        self.critic_agent = critic_agent
        self.skill_manager = skill_manager
        self.executor = executor
        self.session_manager = session_manager

        # Setup PostgreSQL checkpointer for state persistence
        self.checkpointer = self._setup_checkpointer(db_config)

        # Build the graph
        self.graph = self._build_graph()

    def _format_inventory(self, bot_state: BotState) -> str:
        """Format inventory for display."""
        if not bot_state.inventory:
            return "Inventory: Empty"

        items = []
        for item in bot_state.inventory:
            items.append(f"{item.count}x {item.name}")

        return f"Inventory ({len(bot_state.inventory)}/36): {', '.join(items)}"

    def _format_bot_state(self, bot_state: BotState) -> str:
        """Format complete bot state for display."""
        lines = []

        # Health and Hunger
        lines.append(f"Health: {bot_state.health}/20, Hunger: {bot_state.food}/20")

        # Position
        pos = bot_state.position
        lines.append(f"Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")

        # Inventory
        lines.append(self._format_inventory(bot_state))

        # Nearby entities
        if bot_state.nearby_entities:
            entities = []
            for entity in bot_state.nearby_entities[:5]:  # Limit to 5 nearest
                name = entity.name or "unknown"
                entities.append(f"{name} ({entity.distance:.1f}m)")
            lines.append(f"Nearby entities: {', '.join(entities)}")
        else:
            lines.append("Nearby entities: None")

        # Nearby blocks
        if bot_state.nearby_blocks:
            blocks = []
            for block_type, block_info in bot_state.nearby_blocks.items():
                blocks.append(f"{block_type} ({block_info.distance:.1f}m)")
            lines.append(f"Nearby blocks: {', '.join(blocks)}")
        else:
            lines.append("Nearby blocks: None")

        return "\n".join(lines)

    def _setup_checkpointer(self, db_config: Dict[str, str]):
        """Setup PostgreSQL checkpointer for LangGraph."""
        # Create connection string for psycopg3
        conn_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

        # Create connection using psycopg3 with autocommit for CREATE INDEX CONCURRENTLY
        conn = psycopg.connect(conn_string, autocommit=True)

        # Initialize checkpointer with psycopg3 connection
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()

        return checkpointer

    def _build_graph(self):
        """Build the LangGraph state machine."""

        # Create graph
        workflow = StateGraph(VoyagerState)

        # Add nodes
        workflow.add_node("propose_task", self._propose_task_node)
        workflow.add_node("generate_code", self._generate_code_node)
        workflow.add_node("execute_code", self._execute_code_node)
        workflow.add_node("evaluate", self._evaluate_node)
        workflow.add_node("update_skills", self._update_skills_node)

        # Define edges
        workflow.set_entry_point("propose_task")

        workflow.add_edge("propose_task", "generate_code")
        workflow.add_edge("generate_code", "execute_code")
        workflow.add_edge("execute_code", "evaluate")

        # Conditional edge from evaluate
        workflow.add_conditional_edges(
            "evaluate",
            self._should_continue_or_end,
            {
                "update_skills": "update_skills",
                "retry": "generate_code",
                "next_task": "propose_task",
                "end": END,
            },
        )

        workflow.add_edge("update_skills", "propose_task")

        # Compile with checkpointer
        app = workflow.compile(checkpointer=self.checkpointer)

        return app

    def _propose_task_node(self, state: VoyagerState) -> VoyagerState:
        """Node: Propose next task using curriculum agent."""
        print("\n=== PROPOSING TASK ===")

        # Get current bot state
        bot_state = self.executor.get_state()

        # Get completed and failed tasks from session
        completed = [
            t["task_description"]
            for t in self.session_manager.get_completed_tasks(limit=5)
        ]
        failed = [
            t["task_description"]
            for t in self.session_manager.get_failed_tasks(limit=3)
        ]

        # Propose task
        task = self.curriculum_agent.propose_task(
            bot_state=bot_state, completed_tasks=completed, failed_tasks=failed
        )

        print(f"Proposed Task: {task}")
        print(self._format_bot_state(bot_state))

        # Log task in session
        task_id = self.session_manager.log_task(task, status="pending")

        # Log bot state
        self.session_manager.log_bot_state(bot_state, event_type="task_start")

        return {
            **state,
            "task": task,
            "task_id": task_id,
            "bot_state_before": bot_state,
            "iteration": state.get("iteration", 0) + 1,
            "retry_count": 0,
            "completed_tasks": completed,
            "failed_tasks": failed,
        }

    def _generate_code_node(self, state: VoyagerState) -> VoyagerState:
        """Node: Generate code using action agent."""
        print("\n=== GENERATING CODE ===")

        task = state["task"]
        bot_state = state["bot_state_before"]

        # Retrieve relevant skills
        relevant_skills = self.skill_manager.retrieve_skills(task, n_results=3)
        print(f"Retrieved {len(relevant_skills)} relevant skills")

        # Get additional context for better code generation
        code_from_last_round = state.get("generated_code", None)
        execution_error = (
            state.get("execution_result").error
            if state.get("execution_result")
            else None
        )
        chat_log = self.executor.get_chat_log()  # Get chat log from executor
        critique = state.get("critique", None)

        # Generate code with full context
        code = self.action_agent.generate_code(
            task=task,
            bot_state=bot_state,
            relevant_skills=relevant_skills,
            code_from_last_round=code_from_last_round,
            execution_error=execution_error,
            chat_log=chat_log,
            critique=critique,
        )

        print(f"Generated code ({len(code)} characters)")

        return {**state, "generated_code": code, "skills_retrieved": relevant_skills}

    def _execute_code_node(self, state: VoyagerState) -> VoyagerState:
        """Node: Execute generated code in Minecraft."""
        print("\n=== EXECUTING CODE ===")

        code = state["generated_code"]

        # Save generated code to a .js file for examination
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        code_filename = f"generated_code_{timestamp}.js"
        code_filepath = os.path.join("logs", code_filename)

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

        # Write code to file
        with open(code_filepath, "w", encoding="utf-8") as f:
            f.write(f"// Generated code at {datetime.now().isoformat()}\n")
            f.write(f"// Task: {state.get('current_task', 'Unknown')}\n")
            f.write(f"// Attempt: {state.get('retry_count', 0) + 1}\n\n")
            f.write(code)

        print(f"Generated code saved to: {code_filepath}")

        try:
            # Execute code with 60 second timeout
            result = self.executor.execute_code(code, timeout=60)
            print(f"Execution result: {result.success}")

        except Exception as e:
            result = ExecutionResult(success=False, error=str(e))
            print(f"Execution failed: {e}")

        # Get updated bot state
        bot_state_after = self.executor.get_state()

        # Log state after execution
        self.session_manager.log_bot_state(bot_state_after, event_type="task_execute")

        return {**state, "execution_result": result, "bot_state_after": bot_state_after}

    def _evaluate_node(self, state: VoyagerState) -> VoyagerState:
        """Node: Evaluate task completion using critic."""
        print("\n=== EVALUATING ===")

        task = state["task"]
        before_state = state["bot_state_before"]
        after_state = state["bot_state_after"]
        execution_result = state["execution_result"]

        # Evaluate with critic
        evaluation = self.critic_agent.evaluate(
            task=task,
            before_state=before_state,
            after_state=after_state,
            execution_result=execution_result,
        )

        success = evaluation.success
        print(f"Success: {success}")
        print(f"Reasoning: {evaluation.reasoning}")
        print("BEFORE STATE:")
        print(self._format_bot_state(before_state))
        print("AFTER STATE:")
        print(self._format_bot_state(after_state))

        # Update task in session (convert dataclasses to dicts)
        self.session_manager.update_task(
            task_id=state["task_id"],
            status="completed" if success else "in_progress",
            success=success,
            evaluation=asdict(evaluation),
            bot_state_before=(
                asdict(before_state)
                if isinstance(before_state, BotState)
                else before_state
            ),
            bot_state_after=(
                asdict(after_state)
                if isinstance(after_state, BotState)
                else after_state
            ),
            generated_code=state["generated_code"],
            execution_result=asdict(execution_result),
        )

        return {**state, "critic_feedback": evaluation, "success": success}

    def _update_skills_node(self, state: VoyagerState) -> VoyagerState:
        """Node: Update skill library with new skill."""
        print("\n=== UPDATING SKILLS ===")

        task = state["task"]
        code = state["generated_code"]
        success = state["success"]

        if success:
            # Create skill name from task
            skill_name = self._generate_skill_name(task)

            # Add to skill library
            try:
                self.skill_manager.add_skill(
                    name=skill_name, description=task, code=code, tags=["learned"]
                )

                # Log learned skill
                self.session_manager.log_learned_skill(
                    task_id=state["task_id"], skill_name=skill_name, skill_code=code
                )

                print(f"Added new skill: {skill_name}")

            except Exception as e:
                print(f"Failed to add skill: {e}")

        # Mark task as fully completed
        self.session_manager.update_task(task_id=state["task_id"], status="completed")

        return state

    def _should_continue_or_end(self, state: VoyagerState) -> str:
        """Decide next step based on evaluation."""

        success = state.get("success", False)
        retry_count = state.get("retry_count", 0)
        iteration = state.get("iteration", 0)

        # If successful, update skills and move to next task
        if success:
            return "update_skills"

        # If failed but can retry
        if retry_count < 3:  # Max 3 retries
            print(f"Retrying task (attempt {retry_count + 1}/3)")
            state["retry_count"] = retry_count + 1
            return "retry"

        # If max retries reached, mark as failed and move to next task
        print("Max retries reached, moving to next task")
        self.session_manager.update_task(task_id=state["task_id"], status="failed")

        # Continue to next task if under iteration limit
        if iteration < 100:  # Max 100 iterations per session
            return "next_task"
        else:
            return "end"

    def _generate_skill_name(self, task: str) -> str:
        """Generate skill name from task description."""
        # Simple version - just use first few words
        words = task.lower().split()[:3]
        name = "_".join(w.strip(".,!?") for w in words)
        return name

    def run(self, config: Dict[str, Any] = None):
        """Run the Voyager agent loop."""

        # Initial state
        initial_state = {
            "task": "",
            "task_id": 0,
            "iteration": 0,
            "bot_state_before": {},
            "bot_state_after": {},
            "generated_code": "",
            "skills_retrieved": [],
            "execution_result": {},
            "critic_feedback": {},
            "success": False,
            "retry_count": 0,
            "should_continue": True,
            "session_id": self.session_manager.current_session_id,
            "completed_tasks": [],
            "failed_tasks": [],
        }

        # Run graph with increased recursion limit
        thread_config = config or {
            "configurable": {"thread_id": str(self.session_manager.current_session_id)},
            "recursion_limit": 100,  # Increase from default 25 to 100
        }

        print("Starting Voyager agent loop...")

        for output in self.graph.stream(initial_state, thread_config):
            # Print node completion
            for node_name, node_output in output.items():
                print(f"\nCompleted node: {node_name}")

        print("\nVoyager agent loop completed")

        # Print session stats
        stats = self.session_manager.get_session_stats()
        print("\nSession Stats:")
        print(f"  Total tasks: {stats['total_tasks']}")
        print(f"  Successful: {stats['successful_tasks']}")
        print(f"  Failed: {stats['failed_tasks']}")
        print(f"  Skills learned: {stats['skills_learned']}")
