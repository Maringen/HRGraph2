from falkordb import FalkorDB
from config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_DB


class HRGraph:
    def __init__(self):
        self.db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        self.graph = self.db.select_graph(FALKORDB_DB)

    def create_schema(self):
        # Create constraints and indexes
        self.graph.query("CREATE CONSTRAINT ON (e:Employee) ASSERT e.id IS UNIQUE")
        self.graph.query("CREATE CONSTRAINT ON (d:Department) ASSERT d.id IS UNIQUE")
        self.graph.query("CREATE CONSTRAINT ON (p:Position) ASSERT p.id IS UNIQUE")
        self.graph.query("CREATE CONSTRAINT ON (s:Skill) ASSERT s.id IS UNIQUE")

    def add_employee(self, employee):
        query = """
        CREATE (e:Employee {
            id: $id,
            name: $name,
            email: $email,
            hire_date: $hire_date,
            termination_date: $termination_date
        })
        """
        params = employee.dict()
        self.graph.query(query, params)

    def add_department(self, department):
        query = """
        CREATE (d:Department {
            id: $id,
            name: $name,
            manager_id: $manager_id,
            created_date: $created_date
        })
        """
        params = department.dict()
        self.graph.query(query, params)

    def add_position(self, position):
        query = """
        CREATE (p:Position {
            id: $id,
            title: $title,
            department_id: $department_id,
            level: $level,
            start_date: $start_date,
            end_date: $end_date
        })
        """
        params = position.dict()
        self.graph.query(query, params)

    def add_employment(self, employment):
        query = """
        MATCH (e:Employee {id: $employee_id}), (p:Position {id: $position_id})
        CREATE (e)-[:WORKS_IN {
            start_date: $start_date,
            end_date: $end_date
        }]->(p)
        """
        params = employment.dict()
        self.graph.query(query, params)

    def add_skill(self, skill):
        query = """
        CREATE (s:Skill {
            id: $id,
            name: $name,
            description: $description
        })
        """
        params = skill.dict()
        self.graph.query(query, params)

    def add_employee_skill(self, employee_skill):
        query = """
        MATCH (e:Employee {id: $employee_id}), (s:Skill {id: $skill_id})
        CREATE (e)-[:HAS_SKILL {
            acquired_date: $acquired_date,
            proficiency_level: $proficiency_level
        }]->(s)
        """
        params = employee_skill.dict()
        self.graph.query(query, params)
