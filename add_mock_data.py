#!/usr/bin/env python3
"""
Script to add mock HR data to FalkorDB for testing the HR Knowledge Graph.
"""

from falkordb import FalkorDB
from config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_DB
import random
from datetime import datetime, timedelta


def generate_mock_hr_data():
    """Generate comprehensive mock HR data."""

    # Initialize FalkorDB connection
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = db.select_graph(FALKORDB_DB)

    print("Clearing existing data...")
    graph.query("MATCH (n) DETACH DELETE n")

    print("Creating mock HR data...")

    # Create Departments
    departments = [
        {
            "id": "dept_001",
            "name": "Engineering",
            "manager_id": "emp_001",
            "created_date": "2020-01-15",
        },
        {
            "id": "dept_002",
            "name": "Human Resources",
            "manager_id": "emp_005",
            "created_date": "2020-01-15",
        },
        {
            "id": "dept_003",
            "name": "Sales",
            "manager_id": "emp_008",
            "created_date": "2020-02-01",
        },
        {
            "id": "dept_004",
            "name": "Marketing",
            "manager_id": "emp_011",
            "created_date": "2020-02-15",
        },
        {
            "id": "dept_005",
            "name": "Finance",
            "manager_id": "emp_013",
            "created_date": "2020-03-01",
        },
    ]

    for dept in departments:
        graph.query(
            "CREATE (d:Department {id: $id, name: $name, manager_id: $manager_id, created_date: $created_date})",
            dept,
        )

    # Create Positions
    positions = [
        {
            "id": "pos_001",
            "title": "CTO",
            "department_id": "dept_001",
            "level": "Executive",
            "start_date": "2020-01-15",
        },
        {
            "id": "pos_002",
            "title": "Senior Software Engineer",
            "department_id": "dept_001",
            "level": "Senior",
            "start_date": "2020-03-01",
        },
        {
            "id": "pos_003",
            "title": "Software Engineer",
            "department_id": "dept_001",
            "level": "Mid",
            "start_date": "2020-06-01",
        },
        {
            "id": "pos_004",
            "title": "Junior Developer",
            "department_id": "dept_001",
            "level": "Junior",
            "start_date": "2021-01-15",
        },
        {
            "id": "pos_005",
            "title": "HR Director",
            "department_id": "dept_002",
            "level": "Executive",
            "start_date": "2020-01-15",
        },
        {
            "id": "pos_006",
            "title": "HR Manager",
            "department_id": "dept_002",
            "level": "Senior",
            "start_date": "2020-06-01",
        },
        {
            "id": "pos_007",
            "title": "Sales Director",
            "department_id": "dept_003",
            "level": "Executive",
            "start_date": "2020-02-01",
        },
        {
            "id": "pos_008",
            "title": "Sales Manager",
            "department_id": "dept_003",
            "level": "Senior",
            "start_date": "2020-06-01",
        },
        {
            "id": "pos_009",
            "title": "Marketing Director",
            "department_id": "dept_004",
            "level": "Executive",
            "start_date": "2020-02-15",
        },
        {
            "id": "pos_010",
            "title": "CFO",
            "department_id": "dept_005",
            "level": "Executive",
            "start_date": "2020-03-01",
        },
        # Additional positions for new employees
        {
            "id": "pos_011",
            "title": "Staff Engineer",
            "department_id": "dept_001",
            "level": "Senior",
            "start_date": "2022-01-01",
        },
        {
            "id": "pos_012",
            "title": "DevOps Engineer",
            "department_id": "dept_001",
            "level": "Mid",
            "start_date": "2020-11-01",
        },
        {
            "id": "pos_013",
            "title": "Data Scientist",
            "department_id": "dept_001",
            "level": "Mid",
            "start_date": "2021-02-01",
        },
        {
            "id": "pos_014",
            "title": "Security Engineer",
            "department_id": "dept_001",
            "level": "Mid",
            "start_date": "2022-03-01",
        },
        {
            "id": "pos_015",
            "title": "Database Administrator",
            "department_id": "dept_001",
            "level": "Mid",
            "start_date": "2021-08-01",
        },
        {
            "id": "pos_016",
            "title": "Talent Acquisition Specialist",
            "department_id": "dept_002",
            "level": "Mid",
            "start_date": "2021-05-01",
        },
        {
            "id": "pos_017",
            "title": "Benefits Administrator",
            "department_id": "dept_002",
            "level": "Junior",
            "start_date": "2021-05-01",
        },
        {
            "id": "pos_018",
            "title": "Employee Relations Manager",
            "department_id": "dept_002",
            "level": "Mid",
            "start_date": "2020-09-15",
        },
        {
            "id": "pos_019",
            "title": "Account Executive",
            "department_id": "dept_003",
            "level": "Mid",
            "start_date": "2021-04-01",
        },
        {
            "id": "pos_020",
            "title": "Sales Development Rep",
            "department_id": "dept_003",
            "level": "Junior",
            "start_date": "2022-02-15",
        },
        {
            "id": "pos_021",
            "title": "Content Marketing Manager",
            "department_id": "dept_004",
            "level": "Mid",
            "start_date": "2021-06-15",
        },
        {
            "id": "pos_022",
            "title": "Creative Director",
            "department_id": "dept_004",
            "level": "Senior",
            "start_date": "2022-01-10",
        },
        {
            "id": "pos_023",
            "title": "Treasury Manager",
            "department_id": "dept_005",
            "level": "Senior",
            "start_date": "2021-02-01",
        },
        {
            "id": "pos_024",
            "title": "Auditor",
            "department_id": "dept_005",
            "level": "Mid",
            "start_date": "2020-11-15",
        },
        {
            "id": "pos_025",
            "title": "Tax Analyst",
            "department_id": "dept_005",
            "level": "Junior",
            "start_date": "2021-09-01",
        },
    ]

    for pos in positions:
        graph.query(
            "CREATE (p:Position {id: $id, title: $title, department_id: $department_id, level: $level, start_date: $start_date})",
            pos,
        )

    # Create Employees with hire date, promotion date, leave date, and additional data
    employees = [
        # Engineering Department
        {
            "id": "emp_001",
            "name": "John Smith",
            "email": "john.smith@company.com",
            "phone": "+1-555-0101",
            "address": "123 Tech Lane, San Francisco, CA 94102",
            "hire_date": "2020-01-15",
            "promotion_date": "2022-06-01",
            "leave_date": None,
            "salary": 185000,
            "performance_rating": 4.8,
            "skills": ["Leadership", "Architecture", "Python", "Go"],
        },
        {
            "id": "emp_002",
            "name": "Sarah Johnson",
            "email": "sarah.johnson@company.com",
            "phone": "+1-555-0102",
            "address": "456 Code Street, San Francisco, CA 94103",
            "hire_date": "2020-03-01",
            "promotion_date": "2023-01-15",
            "leave_date": None,
            "salary": 155000,
            "performance_rating": 4.5,
            "skills": ["Python", "React", "Node.js", "AWS"],
        },
        {
            "id": "emp_003",
            "name": "Michael Chen",
            "email": "michael.chen@company.com",
            "phone": "+1-555-0103",
            "address": "789 Java Ave, San Francisco, CA 94104",
            "hire_date": "2020-06-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 145000,
            "performance_rating": 4.2,
            "skills": ["Java", "Spring Boot", "Kubernetes", "Docker"],
        },
        {
            "id": "emp_004",
            "name": "Emily Davis",
            "email": "emily.davis@company.com",
            "phone": "+1-555-0104",
            "address": "321 Web Drive, San Francisco, CA 94105",
            "hire_date": "2021-01-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 110000,
            "performance_rating": 4.0,
            "skills": ["JavaScript", "Vue.js", "CSS", "UI/UX"],
        },
        {
            "id": "emp_015",
            "name": "Kevin Rodriguez",
            "email": "kevin.rodriguez@company.com",
            "phone": "+1-555-0115",
            "address": "555 ML Road, San Francisco, CA 94110",
            "hire_date": "2021-02-01",
            "promotion_date": "2024-01-15",
            "leave_date": None,
            "salary": 160000,
            "performance_rating": 4.7,
            "skills": ["Python", "Machine Learning", "Data Science", "TensorFlow"],
        },
        {
            "id": "emp_016",
            "name": "Alex Turner",
            "email": "alex.turner@company.com",
            "phone": "+1-555-0116",
            "address": "888 Frontend Blvd, San Francisco, CA 94111",
            "hire_date": "2020-09-01",
            "promotion_date": None,
            "leave_date": "2023-12-15",
            "salary": 120000,
            "performance_rating": 3.9,
            "skills": ["JavaScript", "React", "TypeScript", "GraphQL"],
        },
        {
            "id": "emp_018",
            "name": "Ryan Cooper",
            "email": "ryan.cooper@company.com",
            "phone": "+1-555-0118",
            "address": "999 Cloud Way, San Francisco, CA 94112",
            "hire_date": "2020-11-01",
            "promotion_date": None,
            "leave_date": "2024-02-28",
            "salary": 140000,
            "performance_rating": 4.1,
            "skills": ["DevOps", "AWS", "Terraform", "CI/CD"],
        },
        {
            "id": "emp_019",
            "name": "Nina Patel",
            "email": "nina.patel@company.com",
            "phone": "+1-555-0119",
            "address": "111 Rust Lane, San Francisco, CA 94113",
            "hire_date": "2022-01-10",
            "promotion_date": None,
            "leave_date": None,
            "salary": 130000,
            "performance_rating": 4.3,
            "skills": ["Rust", "System Design", "Performance", "Go"],
        },
        {
            "id": "emp_020",
            "name": "Carlos Ramirez",
            "email": "carlos.ramirez@company.com",
            "phone": "+1-555-0120",
            "address": "222 Database Drive, San Francisco, CA 94114",
            "hire_date": "2021-08-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 135000,
            "performance_rating": 4.4,
            "skills": ["PostgreSQL", "MongoDB", "Redis", "System Design"],
        },
        {
            "id": "emp_021",
            "name": "Emma Wilson",
            "email": "emma.wilson@company.com",
            "phone": "+1-555-0121",
            "address": "333 Security Ave, San Francisco, CA 94115",
            "hire_date": "2022-03-20",
            "promotion_date": None,
            "leave_date": None,
            "salary": 145000,
            "performance_rating": 4.6,
            "skills": [
                "Cybersecurity",
                "Penetration Testing",
                "Network Security",
                "Python",
            ],
        },
        # Human Resources Department
        {
            "id": "emp_005",
            "name": "Jennifer Wilson",
            "email": "jennifer.wilson@company.com",
            "phone": "+1-555-0205",
            "address": "444 HR Boulevard, San Francisco, CA 94116",
            "hire_date": "2020-01-15",
            "promotion_date": "2021-06-01",
            "leave_date": None,
            "salary": 150000,
            "performance_rating": 4.5,
            "skills": ["HR Management", "Recruitment", "Employee Relations", "HRIS"],
        },
        {
            "id": "emp_006",
            "name": "Robert Brown",
            "email": "robert.brown@company.com",
            "phone": "+1-555-0206",
            "address": "555 Talent Street, San Francisco, CA 94117",
            "hire_date": "2020-06-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 110000,
            "performance_rating": 4.0,
            "skills": [
                "Talent Acquisition",
                "Onboarding",
                "Compliance",
                "Interviewing",
            ],
        },
        {
            "id": "emp_017",
            "name": "Sophie Miller",
            "email": "sophie.miller@company.com",
            "phone": "+1-555-0217",
            "address": "666 People Place, San Francisco, CA 94118",
            "hire_date": "2021-03-15",
            "promotion_date": "2023-06-01",
            "leave_date": None,
            "salary": 125000,
            "performance_rating": 4.4,
            "skills": ["Product Management", "Agile", "Scrum", "Analytics"],
        },
        {
            "id": "emp_022",
            "name": "Amanda Foster",
            "email": "amanda.foster@company.com",
            "phone": "+1-555-0222",
            "address": "777 Benefits Lane, San Francisco, CA 94119",
            "hire_date": "2021-05-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 95000,
            "performance_rating": 4.2,
            "skills": [
                "Benefits Administration",
                "Payroll",
                "HRIS",
                "Employee Wellness",
            ],
        },
        {
            "id": "emp_023",
            "name": "Marcus Johnson",
            "email": "marcus.johnson@company.com",
            "phone": "+1-555-0223",
            "address": "888 Culture Court, San Francisco, CA 94120",
            "hire_date": "2020-09-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 105000,
            "performance_rating": 4.1,
            "skills": [
                "Employee Engagement",
                "Training",
                "DEI",
                "Performance Management",
            ],
        },
        # Sales Department
        {
            "id": "emp_007",
            "name": "David Martinez",
            "email": "david.martinez@company.com",
            "phone": "+1-555-0307",
            "address": "999 Revenue Road, San Francisco, CA 94121",
            "hire_date": "2020-02-01",
            "promotion_date": "2022-06-01",
            "leave_date": None,
            "salary": 165000,
            "performance_rating": 4.7,
            "skills": ["Sales", "Negotiation", "CRM", "Analytics"],
        },
        {
            "id": "emp_008",
            "name": "Lisa Anderson",
            "email": "lisa.anderson@company.com",
            "phone": "+1-555-0308",
            "address": "123 Sales Drive, San Francisco, CA 94122",
            "hire_date": "2020-02-01",
            "promotion_date": "2021-06-01",
            "leave_date": None,
            "salary": 155000,
            "performance_rating": 4.6,
            "skills": [
                "Sales Management",
                "Strategy",
                "Leadership",
                "Business Development",
            ],
        },
        {
            "id": "emp_009",
            "name": "James Taylor",
            "email": "james.taylor@company.com",
            "phone": "+1-555-0309",
            "address": "456 Account Ave, San Francisco, CA 94123",
            "hire_date": "2020-08-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 120000,
            "performance_rating": 4.0,
            "skills": [
                "B2B Sales",
                "Account Management",
                "Revenue Growth",
                "Cold Calling",
            ],
        },
        {
            "id": "emp_024",
            "name": "Rachel Kim",
            "email": "rachel.kim@company.com",
            "phone": "+1-555-0324",
            "address": "789 Deal Street, San Francisco, CA 94124",
            "hire_date": "2021-04-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 115000,
            "performance_rating": 4.3,
            "skills": [
                "Enterprise Sales",
                "Strategic Partnerships",
                "Negotiation",
                "CRM",
            ],
        },
        {
            "id": "emp_025",
            "name": "Tom Hernandez",
            "email": "tom.hernandez@company.com",
            "phone": "+1-555-0325",
            "address": "321 Pipeline Place, San Francisco, CA 94125",
            "hire_date": "2022-02-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 95000,
            "performance_rating": 3.9,
            "skills": ["Lead Generation", "Cold Calling", "SaaS", "Communication"],
        },
        # Marketing Department
        {
            "id": "emp_010",
            "name": "Amanda Thomas",
            "email": "amanda.thomas@company.com",
            "phone": "+1-555-0410",
            "address": "654 Brand Blvd, San Francisco, CA 94126",
            "hire_date": "2020-03-01",
            "promotion_date": "2023-03-01",
            "leave_date": None,
            "salary": 140000,
            "performance_rating": 4.5,
            "skills": ["Digital Marketing", "SEO", "Content Strategy", "Analytics"],
        },
        {
            "id": "emp_011",
            "name": "Christopher Lee",
            "email": "christopher.lee@company.com",
            "phone": "+1-555-0411",
            "address": "987 Campaign Circle, San Francisco, CA 94127",
            "hire_date": "2020-02-15",
            "promotion_date": "2022-01-01",
            "leave_date": None,
            "salary": 155000,
            "performance_rating": 4.6,
            "skills": [
                "Marketing Strategy",
                "Brand Management",
                "Leadership",
                "Market Research",
            ],
        },
        {
            "id": "emp_012",
            "name": "Jessica Garcia",
            "email": "jessica.garcia@company.com",
            "phone": "+1-555-0412",
            "address": "246 Social Media Lane, San Francisco, CA 94128",
            "hire_date": "2020-07-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 115000,
            "performance_rating": 4.2,
            "skills": ["Social Media", "Email Marketing", "PPC", "Analytics"],
        },
        {
            "id": "emp_026",
            "name": "Nicole Adams",
            "email": "nicole.adams@company.com",
            "phone": "+1-555-0426",
            "address": "135 Content Court, San Francisco, CA 94129",
            "hire_date": "2021-06-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 100000,
            "performance_rating": 4.1,
            "skills": ["Content Marketing", "Copywriting", "Blog Management", "SEO"],
        },
        {
            "id": "emp_027",
            "name": " Brandon Wright",
            "email": "brandon.wright@company.com",
            "phone": "+1-555-0427",
            "address": "246 Creative Drive, San Francisco, CA 94130",
            "hire_date": "2022-01-10",
            "promotion_date": None,
            "leave_date": None,
            "salary": 105000,
            "performance_rating": 4.0,
            "skills": [
                "Graphic Design",
                "Adobe Creative Suite",
                "Brand Identity",
                "Video Production",
            ],
        },
        # Finance Department
        {
            "id": "emp_013",
            "name": "Daniel Robinson",
            "email": "daniel.robinson@company.com",
            "phone": "+1-555-0513",
            "address": "369 Finance Way, San Francisco, CA 94131",
            "hire_date": "2020-03-01",
            "promotion_date": "2022-06-01",
            "leave_date": None,
            "salary": 175000,
            "performance_rating": 4.8,
            "skills": ["Financial Planning", "Budgeting", "FP&A", "CFA"],
        },
        {
            "id": "emp_014",
            "name": "Michelle Clark",
            "email": "michelle.clark@company.com",
            "phone": "+1-555-0514",
            "address": "147 Accounting Ave, San Francisco, CA 94132",
            "hire_date": "2020-06-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 120000,
            "performance_rating": 4.3,
            "skills": ["Accounting", "GAAP", "Financial Reporting", "Excel"],
        },
        {
            "id": "emp_028",
            "name": "Victoria Scott",
            "email": "victoria.scott@company.com",
            "phone": "+1-555-0528",
            "address": "258 Treasury Lane, San Francisco, CA 94133",
            "hire_date": "2021-02-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 130000,
            "performance_rating": 4.4,
            "skills": ["Treasury", "Risk Management", "Banking", "Financial Analysis"],
        },
        {
            "id": "emp_029",
            "name": "Eric Thompson",
            "email": "eric.thompson@company.com",
            "phone": "+1-555-0529",
            "address": "369 Audit Street, San Francisco, CA 94134",
            "hire_date": "2020-11-15",
            "promotion_date": None,
            "leave_date": None,
            "salary": 115000,
            "performance_rating": 4.2,
            "skills": ["Auditing", "Compliance", "SOX", "Internal Controls"],
        },
        {
            "id": "emp_030",
            "name": "Laura White",
            "email": "laura.white@company.com",
            "phone": "+1-555-0530",
            "address": "481 Tax Court, San Francisco, CA 94135",
            "hire_date": "2021-09-01",
            "promotion_date": None,
            "leave_date": None,
            "salary": 125000,
            "performance_rating": 4.1,
            "skills": ["Tax Planning", "Tax Compliance", "CPA", "Microsoft Excel"],
        },
    ]

    for emp in employees:
        graph.query(
            """CREATE (e:Employee {id: $id, name: $name, email: $email, phone: $phone, address: $address, 
               hire_date: $hire_date, promotion_date: $promotion_date, leave_date: $leave_date,
               salary: $salary, performance_rating: $performance_rating, skills: $skills})""",
            emp,
        )

    # Create Employment Relationships
    employment_data = [
        # Original employees
        {
            "employee_id": "emp_001",
            "position_id": "pos_001",
            "start_date": "2020-01-15",
        },
        {
            "employee_id": "emp_002",
            "position_id": "pos_002",
            "start_date": "2020-03-01",
        },
        {
            "employee_id": "emp_003",
            "position_id": "pos_003",
            "start_date": "2020-06-15",
        },
        {
            "employee_id": "emp_004",
            "position_id": "pos_004",
            "start_date": "2021-01-15",
        },
        {
            "employee_id": "emp_005",
            "position_id": "pos_005",
            "start_date": "2020-01-15",
        },
        {
            "employee_id": "emp_006",
            "position_id": "pos_006",
            "start_date": "2020-06-01",
        },
        {
            "employee_id": "emp_007",
            "position_id": "pos_007",
            "start_date": "2020-02-01",
        },
        {
            "employee_id": "emp_008",
            "position_id": "pos_008",
            "start_date": "2020-02-01",
        },
        {
            "employee_id": "emp_009",
            "position_id": "pos_009",
            "start_date": "2020-08-01",
        },
        {
            "employee_id": "emp_010",
            "position_id": "pos_010",
            "start_date": "2020-03-01",
        },
        {
            "employee_id": "emp_011",
            "position_id": "pos_011",
            "start_date": "2020-02-15",
        },
        {
            "employee_id": "emp_012",
            "position_id": "pos_012",
            "start_date": "2020-07-01",
        },
        {
            "employee_id": "emp_013",
            "position_id": "pos_013",
            "start_date": "2020-03-01",
        },
        {
            "employee_id": "emp_014",
            "position_id": "pos_014",
            "start_date": "2020-06-15",
        },
        {
            "employee_id": "emp_015",
            "position_id": "pos_015",
            "start_date": "2021-02-01",
        },
        {
            "employee_id": "emp_016",
            "position_id": "pos_003",
            "start_date": "2020-09-01",
        },
        {
            "employee_id": "emp_017",
            "position_id": "pos_006",
            "start_date": "2021-03-15",
        },
        {
            "employee_id": "emp_018",
            "position_id": "pos_002",
            "start_date": "2020-11-01",
        },
        # New employees - Engineering
        {
            "employee_id": "emp_019",
            "position_id": "pos_011",
            "start_date": "2022-01-10",
        },
        {
            "employee_id": "emp_020",
            "position_id": "pos_015",
            "start_date": "2021-08-15",
        },
        {
            "employee_id": "emp_021",
            "position_id": "pos_014",
            "start_date": "2022-03-20",
        },
        # New employees - HR
        {
            "employee_id": "emp_022",
            "position_id": "pos_017",
            "start_date": "2021-05-01",
        },
        {
            "employee_id": "emp_023",
            "position_id": "pos_018",
            "start_date": "2020-09-15",
        },
        # New employees - Sales
        {
            "employee_id": "emp_024",
            "position_id": "pos_019",
            "start_date": "2021-04-01",
        },
        {
            "employee_id": "emp_025",
            "position_id": "pos_020",
            "start_date": "2022-02-15",
        },
        # New employees - Marketing
        {
            "employee_id": "emp_026",
            "position_id": "pos_021",
            "start_date": "2021-06-15",
        },
        {
            "employee_id": "emp_027",
            "position_id": "pos_022",
            "start_date": "2022-01-10",
        },
        # New employees - Finance
        {
            "employee_id": "emp_028",
            "position_id": "pos_023",
            "start_date": "2021-02-01",
        },
        {
            "employee_id": "emp_029",
            "position_id": "pos_024",
            "start_date": "2020-11-15",
        },
        {
            "employee_id": "emp_030",
            "position_id": "pos_025",
            "start_date": "2021-09-01",
        },
    ]

    for emp in employment_data:
        graph.query(
            "MATCH (e:Employee {id: $employee_id}), (p:Position {id: $position_id}) CREATE (e)-[:WORKS_IN {start_date: $start_date}]->(p)",
            emp,
        )

    # Create Department Relationships
    dept_relationships = [
        # Engineering
        {"employee_id": "emp_001", "dept_id": "dept_001", "start_date": "2020-01-15"},
        {"employee_id": "emp_002", "dept_id": "dept_001", "start_date": "2020-03-01"},
        {"employee_id": "emp_003", "dept_id": "dept_001", "start_date": "2020-06-15"},
        {"employee_id": "emp_004", "dept_id": "dept_001", "start_date": "2021-01-15"},
        {"employee_id": "emp_015", "dept_id": "dept_001", "start_date": "2021-02-01"},
        {"employee_id": "emp_016", "dept_id": "dept_001", "start_date": "2020-09-01"},
        {"employee_id": "emp_018", "dept_id": "dept_001", "start_date": "2020-11-01"},
        {"employee_id": "emp_019", "dept_id": "dept_001", "start_date": "2022-01-10"},
        {"employee_id": "emp_020", "dept_id": "dept_001", "start_date": "2021-08-15"},
        {"employee_id": "emp_021", "dept_id": "dept_001", "start_date": "2022-03-20"},
        # HR
        {"employee_id": "emp_005", "dept_id": "dept_002", "start_date": "2020-01-15"},
        {"employee_id": "emp_006", "dept_id": "dept_002", "start_date": "2020-06-01"},
        {"employee_id": "emp_017", "dept_id": "dept_002", "start_date": "2021-03-15"},
        {"employee_id": "emp_022", "dept_id": "dept_002", "start_date": "2021-05-01"},
        {"employee_id": "emp_023", "dept_id": "dept_002", "start_date": "2020-09-15"},
        # Sales
        {"employee_id": "emp_007", "dept_id": "dept_003", "start_date": "2020-02-01"},
        {"employee_id": "emp_008", "dept_id": "dept_003", "start_date": "2020-02-01"},
        {"employee_id": "emp_009", "dept_id": "dept_003", "start_date": "2020-08-01"},
        {"employee_id": "emp_024", "dept_id": "dept_003", "start_date": "2021-04-01"},
        {"employee_id": "emp_025", "dept_id": "dept_003", "start_date": "2022-02-15"},
        # Marketing
        {"employee_id": "emp_010", "dept_id": "dept_004", "start_date": "2020-03-01"},
        {"employee_id": "emp_011", "dept_id": "dept_004", "start_date": "2020-02-15"},
        {"employee_id": "emp_012", "dept_id": "dept_004", "start_date": "2020-07-01"},
        {"employee_id": "emp_026", "dept_id": "dept_004", "start_date": "2021-06-15"},
        {"employee_id": "emp_027", "dept_id": "dept_004", "start_date": "2022-01-10"},
        # Finance
        {"employee_id": "emp_013", "dept_id": "dept_005", "start_date": "2020-03-01"},
        {"employee_id": "emp_014", "dept_id": "dept_005", "start_date": "2020-06-15"},
        {"employee_id": "emp_028", "dept_id": "dept_005", "start_date": "2021-02-01"},
        {"employee_id": "emp_029", "dept_id": "dept_005", "start_date": "2020-11-15"},
        {"employee_id": "emp_030", "dept_id": "dept_005", "start_date": "2021-09-01"},
    ]

    for rel in dept_relationships:
        graph.query(
            "MATCH (e:Employee {id: $employee_id}), (d:Department {id: $dept_id}) CREATE (e)-[:BELONGS_TO {start_date: $start_date}]->(d)",
            rel,
        )

    # Create Skills (expanded list)
    skills_data = [
        {"id": "skill_001", "name": "Python", "category": "Programming"},
        {"id": "skill_002", "name": "JavaScript", "category": "Programming"},
        {"id": "skill_003", "name": "Java", "category": "Programming"},
        {"id": "skill_004", "name": "Go", "category": "Programming"},
        {"id": "skill_005", "name": "React", "category": "Frontend"},
        {"id": "skill_006", "name": "Node.js", "category": "Backend"},
        {"id": "skill_007", "name": "AWS", "category": "Cloud"},
        {"id": "skill_008", "name": "Kubernetes", "category": "DevOps"},
        {"id": "skill_009", "name": "Docker", "category": "DevOps"},
        {"id": "skill_010", "name": "Spring Boot", "category": "Backend"},
        {"id": "skill_011", "name": "Machine Learning", "category": "AI/ML"},
        {"id": "skill_012", "name": "Data Science", "category": "AI/ML"},
        {"id": "skill_013", "name": "TensorFlow", "category": "AI/ML"},
        {"id": "skill_014", "name": "Leadership", "category": "Soft Skills"},
        {"id": "skill_015", "name": "Communication", "category": "Soft Skills"},
        {"id": "skill_016", "name": "Project Management", "category": "Management"},
        {"id": "skill_017", "name": "Sales", "category": "Business"},
        {"id": "skill_018", "name": "Negotiation", "category": "Business"},
        {"id": "skill_019", "name": "Marketing Strategy", "category": "Marketing"},
        {"id": "skill_020", "name": "SEO", "category": "Marketing"},
        {"id": "skill_021", "name": "Financial Planning", "category": "Finance"},
        {"id": "skill_022", "name": "Budgeting", "category": "Finance"},
        {"id": "skill_023", "name": "HR Management", "category": "HR"},
        {"id": "skill_024", "name": "Recruitment", "category": "HR"},
        {"id": "skill_025", "name": "Vue.js", "category": "Frontend"},
        {"id": "skill_026", "name": "CSS", "category": "Frontend"},
        {"id": "skill_027", "name": "UI/UX", "category": "Design"},
        {"id": "skill_028", "name": "Analytics", "category": "Data"},
        {"id": "skill_029", "name": "CRM", "category": "Business"},
        {"id": "skill_030", "name": "Strategic Planning", "category": "Management"},
        {"id": "skill_031", "name": "TypeScript", "category": "Programming"},
        {"id": "skill_032", "name": "Terraform", "category": "DevOps"},
        {"id": "skill_033", "name": "CI/CD", "category": "DevOps"},
        {"id": "skill_034", "name": "Product Management", "category": "Management"},
        {"id": "skill_035", "name": "Agile", "category": "Management"},
        {"id": "skill_036", "name": "Scrum", "category": "Management"},
    ]

    for skill in skills_data:
        graph.query(
            "CREATE (s:Skill {id: $id, name: $name, category: $category})", skill
        )

    # Create Employee-Skill Proficiency Relationships
    # Format: Employee is proficient in Skill
    employee_skills = [
        # John Smith (CTO)
        {
            "employee_id": "emp_001",
            "skill_id": "skill_001",
            "proficiency": "Expert",
            "years": 10,
        },  # Python
        {
            "employee_id": "emp_001",
            "skill_id": "skill_004",
            "proficiency": "Expert",
            "years": 8,
        },  # Go
        {
            "employee_id": "emp_001",
            "skill_id": "skill_014",
            "proficiency": "Expert",
            "years": 15,
        },  # Leadership
        {
            "employee_id": "emp_001",
            "skill_id": "skill_030",
            "proficiency": "Expert",
            "years": 12,
        },  # Strategic Planning
        # Sarah Johnson (Senior Engineer)
        {
            "employee_id": "emp_002",
            "skill_id": "skill_001",
            "proficiency": "Expert",
            "years": 6,
        },  # Python
        {
            "employee_id": "emp_002",
            "skill_id": "skill_005",
            "proficiency": "Expert",
            "years": 5,
        },  # React
        {
            "employee_id": "emp_002",
            "skill_id": "skill_006",
            "proficiency": "Advanced",
            "years": 4,
        },  # Node.js
        {
            "employee_id": "emp_002",
            "skill_id": "skill_007",
            "proficiency": "Advanced",
            "years": 3,
        },  # AWS
        # Michael Chen (Engineer)
        {
            "employee_id": "emp_003",
            "skill_id": "skill_003",
            "proficiency": "Expert",
            "years": 7,
        },  # Java
        {
            "employee_id": "emp_003",
            "skill_id": "skill_010",
            "proficiency": "Expert",
            "years": 5,
        },  # Spring Boot
        {
            "employee_id": "emp_003",
            "skill_id": "skill_008",
            "proficiency": "Advanced",
            "years": 4,
        },  # Kubernetes
        {
            "employee_id": "emp_003",
            "skill_id": "skill_009",
            "proficiency": "Advanced",
            "years": 4,
        },  # Docker
        # Emily Davis (Junior Developer)
        {
            "employee_id": "emp_004",
            "skill_id": "skill_002",
            "proficiency": "Advanced",
            "years": 3,
        },  # JavaScript
        {
            "employee_id": "emp_004",
            "skill_id": "skill_025",
            "proficiency": "Advanced",
            "years": 2,
        },  # Vue.js
        {
            "employee_id": "emp_004",
            "skill_id": "skill_026",
            "proficiency": "Expert",
            "years": 4,
        },  # CSS
        {
            "employee_id": "emp_004",
            "skill_id": "skill_027",
            "proficiency": "Advanced",
            "years": 2,
        },  # UI/UX
        # Jennifer Wilson (HR Director)
        {
            "employee_id": "emp_005",
            "skill_id": "skill_023",
            "proficiency": "Expert",
            "years": 12,
        },  # HR Management
        {
            "employee_id": "emp_005",
            "skill_id": "skill_024",
            "proficiency": "Expert",
            "years": 10,
        },  # Recruitment
        {
            "employee_id": "emp_005",
            "skill_id": "skill_014",
            "proficiency": "Advanced",
            "years": 8,
        },  # Leadership
        {
            "employee_id": "emp_005",
            "skill_id": "skill_015",
            "proficiency": "Expert",
            "years": 10,
        },  # Communication
        # Robert Brown (HR Manager)
        {
            "employee_id": "emp_006",
            "skill_id": "skill_024",
            "proficiency": "Advanced",
            "years": 5,
        },  # Recruitment
        {
            "employee_id": "emp_006",
            "skill_id": "skill_016",
            "proficiency": "Advanced",
            "years": 4,
        },  # Project Management
        {
            "employee_id": "emp_006",
            "skill_id": "skill_015",
            "proficiency": "Advanced",
            "years": 4,
        },  # Communication
        # David Martinez (Sales Director)
        {
            "employee_id": "emp_007",
            "skill_id": "skill_017",
            "proficiency": "Expert",
            "years": 10,
        },  # Sales
        {
            "employee_id": "emp_007",
            "skill_id": "skill_018",
            "proficiency": "Expert",
            "years": 8,
        },  # Negotiation
        {
            "employee_id": "emp_007",
            "skill_id": "skill_029",
            "proficiency": "Advanced",
            "years": 6,
        },  # CRM
        {
            "employee_id": "emp_007",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 5,
        },  # Analytics
        # Lisa Anderson (Sales Manager)
        {
            "employee_id": "emp_008",
            "skill_id": "skill_017",
            "proficiency": "Expert",
            "years": 8,
        },  # Sales
        {
            "employee_id": "emp_008",
            "skill_id": "skill_030",
            "proficiency": "Advanced",
            "years": 5,
        },  # Strategic Planning
        {
            "employee_id": "emp_008",
            "skill_id": "skill_014",
            "proficiency": "Advanced",
            "years": 6,
        },  # Leadership
        {
            "employee_id": "emp_008",
            "skill_id": "skill_018",
            "proficiency": "Advanced",
            "years": 5,
        },  # Negotiation
        # James Taylor (Sales)
        {
            "employee_id": "emp_009",
            "skill_id": "skill_017",
            "proficiency": "Advanced",
            "years": 4,
        },  # Sales
        {
            "employee_id": "emp_009",
            "skill_id": "skill_029",
            "proficiency": "Advanced",
            "years": 3,
        },  # CRM
        {
            "employee_id": "emp_009",
            "skill_id": "skill_028",
            "proficiency": "Intermediate",
            "years": 2,
        },  # Analytics
        # Amanda Thomas (Marketing)
        {
            "employee_id": "emp_010",
            "skill_id": "skill_019",
            "proficiency": "Advanced",
            "years": 5,
        },  # Marketing Strategy
        {
            "employee_id": "emp_010",
            "skill_id": "skill_020",
            "proficiency": "Expert",
            "years": 6,
        },  # SEO
        {
            "employee_id": "emp_010",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 4,
        },  # Analytics
        {
            "employee_id": "emp_010",
            "skill_id": "skill_015",
            "proficiency": "Advanced",
            "years": 5,
        },  # Communication
        # Christopher Lee (Marketing Director)
        {
            "employee_id": "emp_011",
            "skill_id": "skill_019",
            "proficiency": "Expert",
            "years": 10,
        },  # Marketing Strategy
        {
            "employee_id": "emp_011",
            "skill_id": "skill_014",
            "proficiency": "Expert",
            "years": 8,
        },  # Leadership
        {
            "employee_id": "emp_011",
            "skill_id": "skill_030",
            "proficiency": "Advanced",
            "years": 6,
        },  # Strategic Planning
        {
            "employee_id": "emp_011",
            "skill_id": "skill_015",
            "proficiency": "Advanced",
            "years": 7,
        },  # Communication
        # Jessica Garcia (Marketing)
        {
            "employee_id": "emp_012",
            "skill_id": "skill_002",
            "proficiency": "Advanced",
            "years": 4,
        },  # JavaScript
        {
            "employee_id": "emp_012",
            "skill_id": "skill_019",
            "proficiency": "Intermediate",
            "years": 3,
        },  # Marketing Strategy
        {
            "employee_id": "emp_012",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 4,
        },  # Analytics
        {
            "employee_id": "emp_012",
            "skill_id": "skill_020",
            "proficiency": "Advanced",
            "years": 3,
        },  # SEO
        # Daniel Robinson (CFO)
        {
            "employee_id": "emp_013",
            "skill_id": "skill_021",
            "proficiency": "Expert",
            "years": 15,
        },  # Financial Planning
        {
            "employee_id": "emp_013",
            "skill_id": "skill_022",
            "proficiency": "Expert",
            "years": 12,
        },  # Budgeting
        {
            "employee_id": "emp_013",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 8,
        },  # Analytics
        {
            "employee_id": "emp_013",
            "skill_id": "skill_014",
            "proficiency": "Advanced",
            "years": 10,
        },  # Leadership
        # Michelle Clark (Finance)
        {
            "employee_id": "emp_014",
            "skill_id": "skill_022",
            "proficiency": "Expert",
            "years": 8,
        },  # Budgeting
        {
            "employee_id": "emp_014",
            "skill_id": "skill_021",
            "proficiency": "Advanced",
            "years": 6,
        },  # Financial Planning
        {
            "employee_id": "emp_014",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 5,
        },  # Analytics
        {
            "employee_id": "emp_014",
            "skill_id": "skill_015",
            "proficiency": "Intermediate",
            "years": 4,
        },  # Communication
        # Kevin Rodriguez (Data Scientist)
        {
            "employee_id": "emp_015",
            "skill_id": "skill_001",
            "proficiency": "Advanced",
            "years": 4,
        },  # Python
        {
            "employee_id": "emp_015",
            "skill_id": "skill_011",
            "proficiency": "Expert",
            "years": 5,
        },  # Machine Learning
        {
            "employee_id": "emp_015",
            "skill_id": "skill_012",
            "proficiency": "Expert",
            "years": 5,
        },  # Data Science
        {
            "employee_id": "emp_015",
            "skill_id": "skill_013",
            "proficiency": "Advanced",
            "years": 3,
        },  # TensorFlow
        # Alex Turner (Left employee - JavaScript, React)
        {
            "employee_id": "emp_016",
            "skill_id": "skill_002",
            "proficiency": "Expert",
            "years": 5,
        },  # JavaScript
        {
            "employee_id": "emp_016",
            "skill_id": "skill_005",
            "proficiency": "Expert",
            "years": 4,
        },  # React
        {
            "employee_id": "emp_016",
            "skill_id": "skill_002",
            "proficiency": "Advanced",
            "years": 3,
        },  # TypeScript
        {
            "employee_id": "emp_016",
            "skill_id": "skill_006",
            "proficiency": "Advanced",
            "years": 3,
        },  # GraphQL
        # Sophie Miller (Product Manager)
        {
            "employee_id": "emp_017",
            "skill_id": "skill_016",
            "proficiency": "Expert",
            "years": 6,
        },  # Project Management
        {
            "employee_id": "emp_017",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 5,
        },  # Analytics
        {
            "employee_id": "emp_017",
            "skill_id": "skill_015",
            "proficiency": "Expert",
            "years": 7,
        },  # Communication
        {
            "employee_id": "emp_017",
            "skill_id": "skill_030",
            "proficiency": "Advanced",
            "years": 4,
        },  # Strategic Planning
        # Ryan Cooper (DevOps - Left employee)
        {
            "employee_id": "emp_018",
            "skill_id": "skill_007",
            "proficiency": "Expert",
            "years": 6,
        },  # AWS
        {
            "employee_id": "emp_018",
            "skill_id": "skill_008",
            "proficiency": "Advanced",
            "years": 4,
        },  # Kubernetes
        {
            "employee_id": "emp_018",
            "skill_id": "skill_001",
            "proficiency": "Intermediate",
            "years": 3,
        },  # Python
        {
            "employee_id": "emp_018",
            "skill_id": "skill_028",
            "proficiency": "Advanced",
            "years": 5,
        },  # Analytics
    ]

    print("Creating employee-skill proficiency relationships...")
    for rel in employee_skills:
        graph.query(
            """MATCH (e:Employee {id: $employee_id}), (s:Skill {id: $skill_id}) 
               CREATE (e)-[:PROFICIENT_IN {proficiency: $proficiency, years_experience: $years}]->(s)""",
            rel,
        )

    # Count proficiency relationships
    result = graph.query("MATCH ()-[r:PROFICIENT_IN]->() RETURN count(r) as count")
    prof_count = result.result_set[0][0]
    print(f"- Created {prof_count} proficiency relationships")

    # Create additional relationships between employees for collaboration
    collaborations = [
        {"emp1": "emp_001", "emp2": "emp_002", "project": "HR Portal"},
        {"emp1": "emp_002", "emp2": "emp_003", "project": "HR Portal"},
        {"emp1": "emp_002", "emp2": "emp_015", "project": "Data Pipeline"},
        {"emp1": "emp_003", "emp2": "emp_015", "project": "Data Pipeline"},
        {"emp1": "emp_010", "emp2": "emp_011", "project": "Marketing Campaign"},
        {"emp1": "emp_007", "emp2": "emp_009", "project": "Q4 Sales"},
        {"emp1": "emp_016", "emp2": "emp_002", "project": "Mobile App"},
        {"emp1": "emp_017", "emp2": "emp_005", "project": "HR System"},
        {"emp1": "emp_018", "emp2": "emp_001", "project": "Infrastructure"},
    ]

    for collab in collaborations:
        graph.query(
            """MATCH (e1:Employee {id: $emp1}), (e2:Employee {id: $emp2})
               CREATE (e1)-[:COLLABORATES_WITH {project: $project}]->(e2)""",
            collab,
        )

    print(f"- Created {len(collaborations)} collaboration relationships")

    # Create Projects
    projects = [
        {
            "id": "proj_001",
            "title": "HR Portal v2.0",
            "status": "In Progress",
            "lead": "emp_001",
            "start_date": "2024-01-15",
        },
        {
            "id": "proj_002",
            "title": "Data Pipeline",
            "status": "Completed",
            "lead": "emp_003",
            "start_date": "2023-06-01",
        },
        {
            "id": "proj_003",
            "title": "Mobile App",
            "status": "In Progress",
            "lead": "emp_002",
            "start_date": "2024-02-01",
        },
        {
            "id": "proj_004",
            "title": "Q4 Sales Campaign",
            "status": "Planning",
            "lead": "emp_008",
            "start_date": "2024-10-01",
        },
    ]

    for proj in projects:
        graph.query(
            "CREATE (p:Project {id: $id, title: $title, status: $status, lead: $lead, start_date: $start_date})",
            proj,
        )

    # Create Team Relationships
    team_data = [
        {"employee_id": "emp_002", "project_id": "proj_001"},
        {"employee_id": "emp_003", "project_id": "proj_001"},
        {"employee_id": "emp_004", "project_id": "proj_001"},
        {"employee_id": "emp_002", "project_id": "proj_003"},
        {"employee_id": "emp_004", "project_id": "proj_003"},
        {"employee_id": "emp_016", "project_id": "proj_003"},
        {"employee_id": "emp_003", "project_id": "proj_002"},
        {"employee_id": "emp_015", "project_id": "proj_002"},
        {"employee_id": "emp_018", "project_id": "proj_002"},
        {"employee_id": "emp_008", "project_id": "proj_004"},
        {"employee_id": "emp_009", "project_id": "proj_004"},
        {"employee_id": "emp_005", "project_id": "proj_001"},
        {"employee_id": "emp_017", "project_id": "proj_001"},
    ]

    for team in team_data:
        graph.query(
            "MATCH (e:Employee {id: $employee_id}), (p:Project {id: $project_id}) CREATE (e)-[:WORKS_ON]->(p)",
            team,
        )

    # Create Reporting Lines
    reporting_lines = [
        {"employee_id": "emp_002", "manager_id": "emp_001"},
        {"employee_id": "emp_003", "manager_id": "emp_002"},
        {"employee_id": "emp_004", "manager_id": "emp_003"},
        {"employee_id": "emp_015", "manager_id": "emp_002"},
        {"employee_id": "emp_016", "manager_id": "emp_002"},
        {"employee_id": "emp_018", "manager_id": "emp_002"},
        {"employee_id": "emp_006", "manager_id": "emp_005"},
        {"employee_id": "emp_017", "manager_id": "emp_005"},
        {"employee_id": "emp_009", "manager_id": "emp_008"},
        {"employee_id": "emp_012", "manager_id": "emp_011"},
        {"employee_id": "emp_014", "manager_id": "emp_013"},
    ]

    for line in reporting_lines:
        graph.query(
            "MATCH (e:Employee {id: $employee_id}), (m:Employee {id: $manager_id}) CREATE (e)-[:REPORTS_TO]->(m)",
            line,
        )

    print("Mock HR data successfully created!")
    print(f"- {len(departments)} Departments")
    print(f"- {len(positions)} Positions")
    print(f"- {len(employees)} Employees")
    print(f"- {len(skills_data)} Skills")
    print(f"- {len(projects)} Projects")
    print(f"- {len(employee_skills)} Proficiency Relationships")
    print(f"- {len(collaborations)} Collaboration Relationships")

    return True


if __name__ == "__main__":
    try:
        generate_mock_hr_data()
        print("\n✅ Mock data generation completed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
