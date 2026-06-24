import unittest

from database import (
    create_inquiry_opportunity,
    get_connection,
    get_execution_dashboard_data,
    get_open_loop_score,
    init_db,
)


class ExecutionEngineSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created = {"opportunities": [], "tasks": []}

    def tearDown(self):
        conn = get_connection()
        for task_id in self.created["tasks"]:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        for opportunity_id in self.created["opportunities"]:
            conn.execute("DELETE FROM tasks WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM activities WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
        conn.commit()
        conn.close()

    def test_inquiry_task_is_money_is_here(self):
        result = create_inquiry_opportunity(
            {
                "opportunity_name": "__Execution Inquiry Smoke__",
                "company_name": "__Execution Org__",
                "contact_person": "__Execution Contact__",
                "service_type": "Air Freight",
                "trade_lane": "Vietnam -> Los Angeles",
                "next_action": "Prepare quotation",
            }
        )
        self.created["opportunities"].append(result["opportunity_id"])

        dashboard = get_execution_dashboard_data()
        matching = [
            task
            for task in dashboard["money_is_here"]
            if task.get("opportunity_id") == result["opportunity_id"]
        ]

        self.assertTrue(matching)
        self.assertEqual(matching[0]["money_proximity_score"], 100)
        self.assertEqual(matching[0]["money_tier"], "MONEY IS HERE")

    def test_money_first_ordering_and_open_loop_score(self):
        before_score = get_open_loop_score()
        conn = get_connection()
        cur = conn.cursor()
        admin = cur.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        admin_id = admin["id"] if admin else None
        cur.execute(
            """
            INSERT INTO tasks (
                task_type, title, due_date, status, priority, money_proximity_score, assigned_to
            )
            VALUES ('ui_cosmetic', '__Execution Nice To Have__', date('now'), 'open', 'normal', 0, ?)
            """,
            (admin_id,),
        )
        nice_to_have_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO tasks (task_type, title, status, priority, money_proximity_score)
            VALUES ('quote_follow_up', '__Execution Follow Up Quote__', 'open', 'high', 100)
            """
        )
        money_task_id = cur.lastrowid
        conn.commit()
        conn.close()
        self.created["tasks"].extend([nice_to_have_id, money_task_id])

        dashboard = get_execution_dashboard_data()
        task_ids = [task["id"] for task in dashboard["next_actions"]]

        self.assertLess(task_ids.index(money_task_id), task_ids.index(nice_to_have_id))
        self.assertEqual(get_open_loop_score(), before_score + 1)


if __name__ == "__main__":
    unittest.main()
