"""Seed Fr. CRCE A.Y. 2026-27 curriculum subjects (FE/SE/TE/BE x CE/CSE/ECS/MECH).

Idempotent — deterministic uuid5 ids, get-or-create by (semester, branch, code).
Transcribed from the college autonomous-curriculum documents; per-subject
credits are NOT published per subject, so credits stay NULL (honest gaps
beat invented data).

BE years are documented as a single VII/VIII pool, not split by semester.
This script documents its split explicitly: electives + research/IPR +
seminar + one MDM in VII; project + internship + MDM + honors in VIII.

Categories: mandatory | elective | lab | project | internship | broadening
(broadening = HSSM/MDM/entrepreneurship/communication-type courses).

Usage (from repo root):
    cd backend && ENV=dev DATABASE_BACKEND=postgres \\
        DATABASE_URL='sqlite+aiosqlite:///./lecturemind.db' \\
        .venv/bin/python -m scripts.seed_curriculum
"""
import asyncio
import logging
import sys
import uuid

sys.path.insert(0, ".")

from sqlalchemy import inspect, text

from core.sql_db import _engine, close_sql, init_models, session_maker
from models.orm import Base

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

NAMESPACE = uuid.NAMESPACE_DNS

# (branch_code, semester_number) -> {category: [names]}
# Semester numbers: FE=1-2, SE=3-4, TE=5-6, BE=7-8.
CURRICULUM = {
    # ---------------- FIRST YEAR ----------------
    ("COMPS", 1): {
        "mandatory": ["Matrices and Differential Calculus", "Engineering Chemistry",
                      "Programming Fundamentals (C)", "Digital Electronics"],
        "broadening": ["Innovation and Design Thinking", "Indian Knowledge System",
                       "One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 1"],
    },
    ("COMPS", 2): {
        "mandatory": ["Integral Calculus and Probability Theory", "Engineering Physics",
                      "Engineering Graphics", "Basic Electrical and Electronics Engineering",
                      "Object Oriented Programming with JAVA"],
        "broadening": ["Art of Communication", "One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 2"],
    },
    ("CSE", 1): {
        "mandatory": ["Matrices and Differential Calculus", "Engineering Physics",
                      "Programming Fundamentals (C)", "Basic Electrical and Electronics Engineering",
                      "Engineering Graphics"],
        "broadening": ["One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory"],
    },
    ("CSE", 2): {
        "mandatory": ["Integral Calculus and Probability Theory", "Engineering Chemistry",
                      "Digital Electronics", "Object Oriented Programming with JAVA"],
        "broadening": ["Innovation and Design Thinking", "Indian Knowledge System",
                       "Art of Communication", "One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 1"],
    },
    ("ECS", 1): {
        "mandatory": ["Matrices and Differential Calculus", "Engineering Physics",
                      "Programming Fundamentals (C)", "Basic Electrical and Electronics Engineering",
                      "Engineering Graphics"],
        "broadening": ["One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 2"],
    },
    ("ECS", 2): {
        "mandatory": ["Integral Calculus and Probability Theory", "Engineering Chemistry",
                      "Digital Electronics", "Object Oriented Programming with JAVA"],
        "broadening": ["Innovation and Design Thinking", "Indian Knowledge System",
                       "Art of Communication", "One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 1"],
    },
    ("MECH", 1): {
        "mandatory": ["Matrices and Differential Calculus", "Engineering Chemistry",
                      "Programming Fundamentals (C)", "Digital Electronics"],
        "broadening": ["Innovation and Design Thinking", "Indian Knowledge System",
                       "One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 1"],
    },
    ("MECH", 2): {
        "mandatory": ["Integral Calculus and Probability Theory", "Engineering Physics",
                      "Engineering Graphics", "Basic Electrical and Electronics Engineering",
                      "Object Oriented Programming with JAVA"],
        "broadening": ["Art of Communication", "One Liberal Learning / Co-curricular Course"],
        "lab": ["Skill Laboratory - 2"],
    },
    # ---------------- SECOND YEAR ----------------
    ("COMPS", 3): {
        "mandatory": ["Discrete Mathematics and Graph Theory", "Computer Organization and Architecture",
                      "Data Structures", "Object Oriented Programming with JAVA"],
        "elective": ["Open Elective", "Law for Engineers",
                     "Financial Planning, Taxation and Investment",
                     "MDM Course - 1", "MDM Course - 2", "Double Minor / Honors option"],
        "broadening": ["Modern Indian Languages", "Human Values and Professional Ethics"],
        "project": ["Community Engagement Project"],
    },
    ("COMPS", 4): {
        "mandatory": ["Linear Algebra and Business Statistics", "Database Management Systems",
                      "Analysis of Algorithms", "Operating Systems", "Full Stack Development"],
        "elective": ["Open Elective", "MDM Course - 3", "Double Minor / Honors option"],
        "broadening": ["Technology Entrepreneurship",
                       "Technology Innovation for Sustainable Development"],
    },
    ("CSE", 3): {
        "mandatory": ["Discrete Mathematics and Statistics", "Database Management System",
                      "Data Structures", "Object Oriented Programming with JAVA"],
        "elective": ["Open Elective", "MDM Course - 1", "MDM Course - 2",
                     "Double Minor / Honors option"],
        "broadening": ["Modern Indian Language", "Human Values and Professional Ethics"],
        "project": ["Community Engagement Project"],
    },
    ("CSE", 4): {
        "mandatory": ["Linear Algebra and Business Statistics", "Computer Organization and Architecture",
                      "Analysis of Algorithms", "Data Analytics and Visualization", "Web Programming"],
        "lab": ["Competitive Coding Lab"],
        "elective": ["Open Elective", "MDM Course - 3", "Double Minor / Honors option"],
        "broadening": ["Technology Entrepreneurship",
                       "Technology Innovation for Sustainable Development"],
    },
    ("ECS", 3): {
        "mandatory": ["Electronic Devices and Applications", "Computer Organization and Architecture",
                      "Database Management System", "Object Oriented Programming with JAVA"],
        "elective": ["Open Elective", "MDM Course - 1", "MDM Course - 2",
                     "Double Minor / Honors option"],
        "broadening": ["Modern Indian Language", "Human Values and Professional Ethics"],
        "project": ["Community Engagement Project"],
    },
    ("ECS", 4): {
        "mandatory": ["Mathematics and Numerical Methods", "Analog Electronics Circuits",
                      "Discrete Structures and Automata Theory", "Data Structures"],
        "lab": ["Web Technologies Lab"],
        "elective": ["Open Elective", "MDM Course - 3", "Double Minor / Honors option",
                     "HSSM / Entrepreneurship / Sustainability Component"],
    },
    ("MECH", 3): {
        "mandatory": ["Statistical Techniques and Partial Differential Equations",
                      "Advanced Manufacturing Processes", "Engineering Mechanics"],
        "lab": ["Machine Shop Practice"],
        "elective": ["Open Elective", "MDM Course - 1", "MDM Course - 2",
                     "Double Minor / Honors option"],
        "broadening": ["Modern Indian Language", "Human Values and Professional Ethics"],
        "project": ["Community Engagement Project"],
    },
    ("MECH", 4): {
        "mandatory": ["Thermodynamics", "Mechanics of Solids", "Materials Science and Engineering"],
        "lab": ["Materials and Material Testing Lab", "Thermal Engineering Lab",
                "Computer Aided Machine Drawing"],
        "elective": ["Open Elective", "MDM Course - 3", "Double Minor / Honors option"],
        "broadening": ["Technology Entrepreneurship",
                       "Technology Innovation for Sustainable Development"],
    },
    # ---------------- THIRD YEAR ----------------
    ("COMPS", 5): {
        "mandatory": ["Cryptography and System Security"],
        "elective": ["Blockchain Technology", "Deep Learning and Reinforcement Learning",
                     "Cyber Security", "Big Data Analytics", "Computer Graphics",
                     "Human Machine Interface", "Geographical Information Systems",
                     "System Programming with Compiler Construction",
                     "Multidisciplinary Minor", "Open Elective"],
        "lab": ["Image Processing Laboratory", "Natural Language Processing Laboratory",
                "Industrial IoT Laboratory", "Innovative Product Development Laboratory",
                "Ethical Hacking Laboratory"],
        "broadening": ["MDM / Skill Component"],
    },
    ("COMPS", 6): {
        "elective": ["Decentralized Finance", "Generative AI", "Digital Forensics",
                     "Business Intelligence", "Augmented Reality and Virtual Reality",
                     "UX/UI Design", "Quantum Computing", "Advanced Network Communications"],
        "lab": ["Social Media Analytics Laboratory", "Threat Intelligence Laboratory",
                "Advanced Java Laboratory", "Explainable AI Laboratory"],
    },
    ("CSE", 5): {
        "mandatory": ["Operating System", "Software Engineering"],
        "elective": ["Big Data Analytics", "Blockchain", "Image Processing",
                     "Social Media Analytics", "Graph Data Science", "AI in Cyber Security",
                     "FinTech", "UI/UX Design", "Computer Vision",
                     "Open Elective", "MDM"],
        "lab": ["Knowledge Representation and Ontology Lab", "Generative AI Lab",
                "Soft Computing Lab"],
        "broadening": ["HSSM / Skill Component"],
    },
    ("CSE", 6): {
        "mandatory": ["Cryptography and Computer Security", "Data Warehousing and Mining",
                      "Cloud Computing", "Deep Learning"],
        "lab": ["Software Testing Lab"],
        "elective": ["MDM", "Degree Option Course"],
        "broadening": ["Public Relations and Corporate Communication"],
    },
    ("ECS", 5): {
        "mandatory": ["Control Systems", "VLSI Design", "Artificial Intelligence",
                      "Analysis of Algorithms", "Software Engineering", "Embedded Systems and RTOS"],
        "elective": ["Open Elective", "MDM", "Automation", "Biomedical Instrumentation",
                     "Power Electronics", "Digital Signal Processing", "Analog VLSI Design",
                     "Cryptography", "Natural Language Processing", "Big Data Analytics",
                     "Advanced Algorithms"],
        "lab": ["IoT Laboratory", "Image Processing Lab", "Blockchain Lab",
                "Deep Learning Laboratory", "Software Testing & Quality Assurance Lab"],
    },
    ("ECS", 6): {
        "mandatory": ["Communication and Computer Networks", "Machine Learning",
                      "CAD for VLSI", "System Security"],
        "lab": ["Cloud Computing Lab", "Data Acquisition and Processing Lab"],
        "elective": ["Open Elective", "MDM Component"],
    },
    ("MECH", 5): {
        "mandatory": ["Fluid Mechanics and Hydraulic Machines"],
        "elective": ["Open Elective", "MDM", "Costing and Cost Control",
                     "Mould and Metal Forming Technology", "Additive Manufacturing",
                     "Tool Engineering", "Optimization Techniques", "Project Management",
                     "Industrial Engineering and Operations Management", "Manufacturing Systems",
                     "Finite Element Analysis", "Dynamics of Machinery", "Industrial Robotics",
                     "IC Engines"],
        "lab": ["Additive Manufacturing Laboratory", "Condition Monitoring Laboratory"],
    },
    ("MECH", 6): {
        "mandatory": ["Heat Transfer", "Machine Design"],
        "lab": ["Heat Transfer Laboratory", "Hydraulics and Pneumatics Laboratory",
                "Measurement Systems and Quality Engineering Laboratory", "CNC Laboratory"],
        "elective": ["MDM"],
        "broadening": ["Public Relations and Corporate Communication"],
    },
    # ---------------- FOURTH YEAR (documented VII/VIII pool, split: see module docstring) ----------------
    ("COMPS", 7): {
        "mandatory": ["Essentials of Research Methodology", "Intellectual Property Rights"],
        "elective": ["Quantum Computing", "Big Data Analytics",
                     "Soft Computing and Optimization Algorithms", "AI for Finance Management",
                     "Blockchain Technology", "IT Service Management",
                     "High Performance Computing", "MDM Course - A"],
        "project": ["Course Seminar"],
    },
    ("COMPS", 8): {
        "elective": ["MDM Course - B", "Honors / Minor Course"],
        "project": ["Major Project"],
        "internship": ["Semester-long Internship"],
    },
    ("CSE", 7): {
        "mandatory": ["Essentials of Research Methodology", "Intellectual Property Rights"],
        "elective": ["Natural Language Processing", "Software Engineering", "Quantum Computing",
                     "Big Data Analytics", "Blockchain Technologies", "Optimization Algorithm",
                     "IT Service Management", "MDM Course 6"],
        "project": ["Course Seminar"],
    },
    ("CSE", 8): {
        "elective": ["MDM Course 7", "Honors / Minor Option"],
        "project": ["Capstone Project"],
        "internship": ["Semester-long Internship"],
    },
    ("ECS", 7): {
        "mandatory": ["Essentials of Research Methodology", "Intellectual Property Rights"],
        "elective": ["Power Electronics", "Robotics", "ASIC Verification",
                     "High Performance Computing", "Quantum Computing", "Blockchain Technology",
                     "Soft Computing and Optimization Algorithms",
                     "Product, Services and IT Service Management", "MDM Course 1"],
        "project": ["Course Seminar"],
    },
    ("ECS", 8): {
        "elective": ["MDM Course 2", "Honors / Minor Option"],
        "project": ["Major Project"],
        "internship": ["Semester-long Internship"],
    },
    ("MECH", 7): {
        "mandatory": ["Essentials of Research Methodology", "Intellectual Property Rights"],
        "elective": ["Heating, Ventilation, Air Conditioning and Refrigeration",
                     "Lean Manufacturing", "Design of Material Handling and Power Systems",
                     "Machinery Diagnostics", "Smart Materials",
                     "Finite Element Methods for Engineering Analysis",
                     "Disaster Management", "Environment Management",
                     "Management Information System", "Finance Management",
                     "MDM Course 6"],
        "project": ["Course Seminar"],
    },
    ("MECH", 8): {
        "elective": ["MDM Course 7", "Honors / Minor Option"],
        "project": ["Major Project"],
        "internship": ["Semester-long Internship"],
    },
}

BUCKET_ORDER = ("mandatory", "elective", "lab", "project", "internship", "broadening")


def _uid(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "lectify.curriculum." + ".".join(parts)))


async def _ensure_ddl() -> None:
    await init_models()
    eng = _engine()
    async with eng.begin() as conn:
        def _inspect(sync_conn):
            insp = inspect(sync_conn)
            return (
                {c["name"] for c in insp.get_columns("subjects")},
                sync_conn.execute(text("SELECT COUNT(*) FROM subjects")).scalar(),
            )
        names, count = await conn.run_sync(_inspect)
        if "branch_id" not in names or "category" not in names:
            if count:
                raise RuntimeError(
                    f"subjects table holds {count} legacy rows — migrate manually."
                )
            logger.info("Rebuilding empty subjects table with branch/category columns")
            await conn.run_sync(lambda sc: Base.metadata.tables["subjects"].drop(sc))
            await conn.run_sync(lambda sc: Base.metadata.tables["subjects"].create(sc))


async def seed() -> dict:
    from sqlalchemy import select as sa_select

    from models.orm import BranchORM, SemesterORM, SubjectORM

    counts = {"created": 0, "existing": 0}

    maker = session_maker()
    async with maker() as s:
        branches = {r.code: r for r in (await s.execute(sa_select(BranchORM))).scalars().all()}
        semesters = {r.number: r for r in (await s.execute(sa_select(SemesterORM))).scalars().all()}
        missing_branches = sorted(set(b for b, _ in CURRICULUM) - set(branches))
        missing_sems = sorted(set(n for _, n in CURRICULUM) - set(semesters))
        if missing_branches or missing_sems:
            raise RuntimeError(
                f"Run seed_crce first — missing branches {missing_branches}, "
                f"semesters {missing_sems}"
            )

        async def _get_or_create(model, key, defaults):
            row = (await s.execute(sa_select(model).filter_by(**key))).scalars().first()
            if row is not None:
                return False
            s.add(model(**key, **defaults))
            await s.flush()
            return True

        for (branch_code, sem_no), buckets in CURRICULUM.items():
            branch = branches[branch_code]
            semester = semesters[sem_no]
            idx = 0
            for bucket in BUCKET_ORDER:
                for name in buckets.get(bucket, []):
                    idx += 1
                    code = f"{branch_code}-S{sem_no}-{idx:02d}"
                    created = await _get_or_create(
                        SubjectORM,
                        {"semester_id": semester.id, "branch_id": branch.id, "code": code},
                        {"id": _uid(branch_code, str(sem_no), code),
                         "name": name, "category": bucket},
                    )
                    counts["created" if created else "existing"] += 1
        await s.commit()
    return counts


async def main() -> int:
    await _ensure_ddl()
    try:
        counts = await seed()
    finally:
        await close_sql()
    total = sum(len(v) for buckets in CURRICULUM.values() for v in buckets.values())
    print(f"Curriculum seeding finished: {counts['created']} created, "
          f"{counts['existing']} already existed ({total} in payload).")
    return 0


if __name__ == "__main__":
    import asyncio as _asyncio

    sys.exit(_asyncio.run(main()))
