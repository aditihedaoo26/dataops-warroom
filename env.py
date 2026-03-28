import json
import os
import sqlite3
from typing import Dict, Any, Tuple

class DataOpsWarRoomEnv:
    def __init__(self, scenario_path: str):
        """Initialize the DataOps War Room environment."""
        self.scenario_path = scenario_path
        self.scenario_data = None
        self.current_task_idx = 0
        self.done = False

    def reset(self) -> Dict[str, Any]:
        """Reset the environment, load scenario, and start at task 0."""
        if not os.path.exists(self.scenario_path):
            raise FileNotFoundError(f"Scenario not found: {self.scenario_path}")
            
        with open(self.scenario_path, "r") as f:
            self.scenario_data = json.load(f)
            
        self.current_task_idx = 0
        self.done = False
        return self.state()

    def _grader_1(self, current_task: Dict[str, Any], action: Dict[str, Any]) -> float:
        """
        Phase 2: Task 1 (Incident Triage) Grader.
        """
        score = 0.0
        if action.get("root_cause") == current_task.get("expected_root_cause"):
            score += 0.5
        if action.get("severity") == current_task.get("expected_severity"):
            score += 0.5
        return min(score, 1.0)

    def _grader_2(self, current_task: Dict[str, Any], action: Dict[str, Any]) -> float:
        """
        Phase 3: Task 2 (SQL Optimization) Grader.
        """
        submitted_query = action.get("query", "")
        expected_query = current_task.get("expected_query", "")
        schema_stmts = current_task.get("schema", [])
        data_stmts = current_task.get("data", [])
        
        score = 0.0
        
        try:
            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()
            
            # Setup schema and data
            for stmt in schema_stmts:
                cursor.execute(stmt)
            for stmt in data_stmts:
                cursor.execute(stmt)
            conn.commit()
            
            # Execute expected query
            cursor.execute(expected_query)
            expected_results = cursor.fetchall()
            
            # Execute submitted query
            cursor.execute(submitted_query)
            submitted_results = cursor.fetchall()
            conn.close()
        except Exception:
            return 0.0
            
        # Compare correctness
        if sorted(expected_results) == sorted(submitted_results):
            score += 0.7
            
        # Performance bonus
        optimized = submitted_query.upper()
        uses_join = "JOIN" in optimized
        uses_subquery = "SELECT" in optimized and "IN (" in optimized
        
        if uses_join and not uses_subquery:
            score += 0.3
            
        # Explanation bonus (power move)
        explanation = action.get("explanation", "").lower()
        if "join" in explanation:
            score += 0.1
            
        return min(score, 1.0)

    def _grader_3(self, current_task: Dict[str, Any], action: Dict[str, Any]) -> float:
        """
        Phase 4: Task 3 (Clinical Data Cleaning) Grader.
        """
        dirty_data = current_task.get("dirty_data", [])
        expected_data = current_task.get("expected_cleaned_data", [])
        submitted_data = action.get("cleaned_data", [])
        
        if not isinstance(submitted_data, list) or not submitted_data:
            return 0.0
            
        total_fixes_needed = 0
        correct_fixes = 0
        
        try:
            for i, expected_row in enumerate(expected_data):
                dirty_row = dirty_data[i] if i < len(dirty_data) else {}
                submitted_row = submitted_data[i] if i < len(submitted_data) else {}
                
                for key, expected_val in expected_row.items():
                    dirty_val = dirty_row.get(key)
                    submitted_val = submitted_row.get(key)
                    
                    if dirty_val != expected_val:
                        total_fixes_needed += 1
                        if submitted_val == expected_val:
                            correct_fixes += 1
            
            if total_fixes_needed == 0:
                base_score = 1.0
            else:
                base_score = float(correct_fixes) / total_fixes_needed
                
            # Field-level explanation bonus (power move)
            explanation = action.get("explanation", "").lower()
            if "date" in explanation or "age" in explanation:
                base_score += 0.05
                
            return min(base_score, 1.0)
        except Exception:
            return 0.0

    def _grader_4(self, current_task: Dict[str, Any], action: Dict[str, Any]) -> float:
        """
        Phase 5: Task 4 (Code Review) Grader.
        """
        expected_bug = current_task.get("expected_bug", "").lower()
        expected_fix = current_task.get("expected_fix", "").lower()
        
        submitted_bug = action.get("bug", "")
        submitted_fix = action.get("fix", "")
        
        if not submitted_bug or not submitted_fix:
            return 0.0
            
        score = 0.0
        
        if expected_bug and expected_bug in submitted_bug.lower():
            score += 0.5
            
        if expected_fix and expected_fix in submitted_fix.lower():
            score += 0.5
            
        return min(score, 1.0)

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute an action for the CURRENT task, determine reward,
        and advance to the NEXT task in the incident.
        """
        if self.done:
            return self.state(), 0.0, True, {"error": "Episode is already done."}
        
        current_task = self.scenario_data["tasks"][self.current_task_idx]
        task_type = current_task.get("task_type", current_task.get("task"))
        
        reward = 0.0
        info = {}
        
        # 1. Evaluate the action using the correct grader
        if task_type == "incident_triage":
            reward = self._grader_1(current_task, action)
            info["msg"] = "Task graded."
        elif task_type == "sql_optimization":
            reward = self._grader_2(current_task, action)
            info["msg"] = "SQL Optimization graded."
        elif task_type == "data_cleaning":
            reward = self._grader_3(current_task, action)
            info["msg"] = "Data Cleaning graded."
        elif task_type == "code_review":
            reward = self._grader_4(current_task, action)
            info["msg"] = "Code Review graded."
        else:
            info["error"] = f"Unknown task type: {task_type}"
            
        # 2. Transition to the next task in the scenario workflow
        self.current_task_idx += 1
        
        # 3. Check if we've finished all tasks in this incident
        done = self.current_task_idx >= len(self.scenario_data["tasks"])
        self.done = done
        
        if done:
            info["msg"] = info.get("msg", "") + " Episode Complete."
        else:
            info["msg"] = info.get("msg", "") + " Moving to next task."
            
        return self.state(), reward, done, info

    def state(self) -> Dict[str, Any]:
        """
        Return the state for the *current* task.
        """
        if self.done or not self.scenario_data:
            return {
                "status": "done",
                "message": "Incident resolved successfully"
            }
            
        current_task = self.scenario_data["tasks"][self.current_task_idx]
        task_type = current_task.get("task_type", current_task.get("task"))
        
        # remove expected fields
        visible_task = {k: v for k, v in current_task.items() if not k.startswith("expected_")}
        
        return {
            "task_type": task_type,
            "input": visible_task
        }

# --- Testing Locally ---
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scenario_file = os.path.join(base_dir, "scenarios", "scenario_1.json")
    
    env = DataOpsWarRoomEnv(scenario_file)
    print("--- Testing Phase 2 Episode Flow ---")
    
    state = env.reset()
    print("\n[Observation - Task 1]")
    print(json.dumps(state, indent=2))
    
    action = {"root_cause": "data_quality", "severity": "high"}
    print(f"\n[Taking Action]\n{json.dumps(action)}")
    
    next_state, reward, done, info = env.step(action)
    print(f"\n[Result - Step 1]")
    print(f"Reward: {reward} | Done: {done} | Info: {info}")
    
    print("\n[Next State returned by step()]")
    print(json.dumps(next_state, indent=2))
    
    if not done:
        action2 = {
            "query": "SELECT DISTINCT name FROM patients JOIN visits ON patients.id = visits.patient_id;",
            "explanation": "Replaced subquery with JOIN for better performance"
        }
        print(f"\n[Taking Action 2]\n{json.dumps(action2)}")
        next_state2, reward2, done2, info2 = env.step(action2)
        print(f"\n[Result - Step 2]")
        print(f"Reward: {reward2} | Done: {done2} | Info: {info2}")
        print("\n[Final State]")
        print(json.dumps(next_state2, indent=2))
        
        if not done2:
            action3 = {
                "cleaned_data": [
                    {"patient_id": 1, "age": -1, "gender": "M", "visit_date": "2023-01-12", "lab_value": 45.5},
                    {"patient_id": 2, "age": -1, "gender": "U", "visit_date": "2023-01-13", "lab_value": 30.0},
                    {"patient_id": 3, "age": 45, "gender": "F", "visit_date": "2023-01-14", "lab_value": 0.0}
                ],
                "explanation": "Fixed date format and removed invalid ages"
            }
            print(f"\n[Taking Action 3]\n{json.dumps(action3)}")
            next_state3, reward3, done3, info3 = env.step(action3)
            print(f"\n[Result - Step 3]")
            print(f"Reward: {reward3} | Done: {done3} | Info: {info3}")
            print("\n[Final State 3]")
            print(json.dumps(next_state3, indent=2))
            
            if not done3:
                action4 = {
                    "bug": "The script fails when the age column is completely missing or null.",
                    "fix": "Use a default or handle the None case explicitly."
                }
                print(f"\n[Taking Action 4]\n{json.dumps(action4)}")
                next_state4, reward4, done4, info4 = env.step(action4)
                print(f"\n[Result - Step 4]")
                print(f"Reward: {reward4} | Done: {done4} | Info: {info4}")
                print("\n[Final State 4]")
                print(json.dumps(next_state4, indent=2))
