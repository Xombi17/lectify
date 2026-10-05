"""Realistic college hierarchy seed fixture for Lectify multi-tenant class isolation testing."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, hash_password
from core.sql_db import session_maker
from models.orm import (
    BranchORM,
    ClassORM,
    DivisionORM,
    InstitutionORM,
    LectureORM,
    SemesterORM,
    StudentEnrollmentORM,
    SubjectORM,
    TeacherAssignmentORM,
    TimetableSlotORM,
    UserORM,
)


@dataclass
class CollegeSeedData:
    institution: InstitutionORM
    years: Dict[int, YearORM] = field(default_factory=dict)
    branches: Dict[str, BranchORM] = field(default_factory=dict)
    semesters: Dict[int, SemesterORM] = field(default_factory=dict)
    divisions: Dict[str, DivisionORM] = field(default_factory=dict)
    subjects: Dict[str, SubjectORM] = field(default_factory=dict)
    classes: Dict[str, ClassORM] = field(default_factory=dict)
    users: Dict[str, UserORM] = field(default_factory=dict)
    lectures: Dict[str, LectureORM] = field(default_factory=dict)
    slots: Dict[str, TimetableSlotORM] = field(default_factory=dict)
    tokens: Dict[str, str] = field(default_factory=dict)


async def seed_college_hierarchy(session: Optional[AsyncSession] = None) -> CollegeSeedData:
    """Seed a realistic 4-year engineering college hierarchy:
    - 1 Institution: Apex Institute of Technology
    - 4 Years (Year 1 to Year 4)
    - 4 Branches: COMPS (Computer Eng), CSE (CS & Eng), ELEC (Electronics & CS), MECH (Mechanical)
    - 8 Semesters across the years (Sem 1 to Sem 8)
    - Divisions for Sem 3: Comps A, Comps B, Comps C, CSE A, CSE B
    - Subjects for Sem 3: Operating Systems (CS301), Algorithms (CS302), Networks (CS303)
    - Classes linking Divisions to Subjects
    - Users: Students (Comps A, Comps B, CSE A), Teachers (Comps A, Comps B), Admin
    - Enrollments and Teacher Assignments
    - Published lectures with realistic notes, transcripts, quizzes, embeddings
    - Timetable slots for weekly schedules
    """
    from models.orm import YearORM

    close_session_on_exit = False
    if session is None:
        session = session_maker()()
        close_session_on_exit = True

    data = CollegeSeedData(
        institution=InstitutionORM(
            id=f"inst_{uuid.uuid4().hex[:8]}",
            name="Apex Institute of Technology",
            code=f"AIT_{uuid.uuid4().hex[:4]}",
            address="100 University Parkway, Tech City",
        )
    )

    try:
        session.add(data.institution)
        await session.flush()

        # 1. 4 Years
        year_names = ["First Year (FE)", "Second Year (SE)", "Third Year (TE)", "Final Year (BE)"]
        for num in range(1, 5):
            y = YearORM(
                id=f"yr_{num}_{uuid.uuid4().hex[:6]}",
                institution_id=data.institution.id,
                number=num,
                name=year_names[num - 1],
            )
            session.add(y)
            data.years[num] = y
        await session.flush()

        # 2. 4 Branches
        branches_def = [
            ("COMPS", "Computer Engineering"),
            ("CSE", "Computer Science & Engineering"),
            ("ELEC", "Electronics & Computer Science"),
            ("MECH", "Mechanical Engineering"),
        ]
        for code, name in branches_def:
            b = BranchORM(
                id=f"br_{code.lower()}_{uuid.uuid4().hex[:6]}",
                institution_id=data.institution.id,
                code=code,
                name=name,
            )
            session.add(b)
            data.branches[code] = b
        await session.flush()

        # 3. 8 Semesters (2 per year)
        for s_num in range(1, 9):
            yr_num = (s_num + 1) // 2
            sem = SemesterORM(
                id=f"sem_{s_num}_{uuid.uuid4().hex[:6]}",
                year_id=data.years[yr_num].id,
                number=s_num,
                label=f"Semester {s_num}",
            )
            session.add(sem)
            data.semesters[s_num] = sem
        await session.flush()

        # 4. Divisions for Semester 3 (Year 2)
        sem3 = data.semesters[3]
        div_names = ["Comps A", "Comps B", "Comps C", "CSE A", "CSE B"]
        for dname in div_names:
            slug = dname.lower().replace(" ", "_")
            div = DivisionORM(
                id=f"div_{slug}_{uuid.uuid4().hex[:6]}",
                semester_id=sem3.id,
                name=dname,
                capacity=60,
            )
            session.add(div)
            data.divisions[slug] = div
        await session.flush()

        # 5. Subjects for Semester 3
        subjects_def = [
            ("os", "CS301", "Operating Systems", 4),
            ("dsa", "CS302", "Data Structures & Algorithms", 4),
            ("cn", "CS303", "Computer Networks", 3),
        ]
        for slug, code, name, credits in subjects_def:
            sub = SubjectORM(
                id=f"sub_{slug}_{uuid.uuid4().hex[:6]}",
                semester_id=sem3.id,
                code=code,
                name=name,
                credits=credits,
            )
            session.add(sub)
            data.subjects[slug] = sub
        await session.flush()

        # 6. Classes (Division + Subject pairs)
        class_pairs = [
            ("comps_a_os", "comps_a", "os", "Comps A · Operating Systems"),
            ("comps_b_os", "comps_b", "os", "Comps B · Operating Systems"),
            ("comps_a_dsa", "comps_a", "dsa", "Comps A · DSA"),
            ("cse_a_os", "cse_a", "os", "CSE A · Operating Systems"),
        ]
        for key, div_slug, sub_slug, class_name in class_pairs:
            cls = ClassORM(
                id=f"cls_{key}_{uuid.uuid4().hex[:6]}",
                division_id=data.divisions[div_slug].id,
                subject_id=data.subjects[sub_slug].id,
                name=class_name,
            )
            session.add(cls)
            data.classes[key] = cls
        await session.flush()

        # 7. Users
        pw_hash = hash_password("secret123")
        users_def = [
            ("student_comps_a", "Alice CompsA", "alice.compsa@apex.edu", "student"),
            ("student_comps_b", "Bob CompsB", "bob.compsb@apex.edu", "student"),
            ("student_cse_a", "Charlie CseA", "charlie.csea@apex.edu", "student"),
            ("teacher_comps_a", "Prof Operating Systems A", "prof.compsa@apex.edu", "teacher"),
            ("teacher_comps_b", "Prof Operating Systems B", "prof.compsb@apex.edu", "teacher"),
            ("admin_user", "Dean Academics", "admin@apex.edu", "admin"),
        ]
        for key, name, email, role in users_def:
            u = UserORM(
                id=f"usr_{key}_{uuid.uuid4().hex[:6]}",
                name=name,
                email=f"{uuid.uuid4().hex[:4]}_{email}",
                role=role,
                password_hash=pw_hash,
            )
            session.add(u)
            data.users[key] = u
            data.tokens[key] = create_access_token(
                subject=u.id,
                role=role,
                extra={"email": u.email, "name": u.name},
            )
        await session.flush()

        # 8. Enrollments (Students -> Classes)
        enrollments = [
            ("student_comps_a", "comps_a_os"),
            ("student_comps_a", "comps_a_dsa"),
            ("student_comps_b", "comps_b_os"),
            ("student_cse_a", "cse_a_os"),
        ]
        for stu_key, cls_key in enrollments:
            enr = StudentEnrollmentORM(
                id=f"enr_{uuid.uuid4().hex[:8]}",
                class_id=data.classes[cls_key].id,
                student_id=data.users[stu_key].id,
            )
            session.add(enr)
        await session.flush()

        # 9. Teacher Assignments (Teachers -> Classes)
        assignments = [
            ("teacher_comps_a", "comps_a_os"),
            ("teacher_comps_a", "comps_a_dsa"),
            ("teacher_comps_b", "comps_b_os"),
        ]
        for tea_key, cls_key in assignments:
            ta = TeacherAssignmentORM(
                id=f"ta_{uuid.uuid4().hex[:8]}",
                class_id=data.classes[cls_key].id,
                teacher_id=data.users[tea_key].id,
                active=True,
            )
            session.add(ta)
        await session.flush()

        # 10. Timetable Slots
        slots_def = [
            ("comps_a_os_slot", "comps_a_os", "teacher_comps_a", 0, "09:00", "10:30", "Lab 201"),
            ("comps_b_os_slot", "comps_b_os", "teacher_comps_b", 1, "11:00", "12:30", "Lab 202"),
        ]
        for key, cls_key, tea_key, dow, st, et, room in slots_def:
            slot = TimetableSlotORM(
                id=f"slot_{key}_{uuid.uuid4().hex[:6]}",
                class_id=data.classes[cls_key].id,
                teacher_id=data.users[tea_key].id,
                day_of_week=dow,
                start_time=st,
                end_time=et,
                room=room,
            )
            session.add(slot)
            data.slots[key] = slot
        await session.flush()

        # 11. Lectures with materials, embeddings, transcripts
        now = datetime.now(timezone.utc)
        lectures_def = [
            (
                "comps_a_lec",
                "comps_a_os",
                "teacher_comps_a",
                "comps_a_os_slot",
                "Comps A OS: Virtual Memory and Paging",
                "Demand paging, page tables, and TLB mechanisms explained for Comps Division A.",
                ["paging", "page tables", "tlb", "comps-a-exclusive"],
                [0.9, 0.1, 0.0],
            ),
            (
                "comps_b_lec",
                "comps_b_os",
                "teacher_comps_b",
                "comps_b_os_slot",
                "Comps B OS: Inverted Page Tables & Working Sets",
                "Inverted page tables and thrashing avoidance strictly for Comps Division B.",
                ["inverted page table", "thrashing", "comps-b-secret"],
                [0.1, 0.9, 0.0],
            ),
        ]
        for key, cls_key, tea_key, slot_key, title, summary, concepts, emb in lectures_def:
            lec = LectureORM(
                id=f"lec_{key}_{uuid.uuid4().hex[:6]}",
                teacher_id=data.users[tea_key].id,
                class_id=data.classes[cls_key].id,
                timetable_slot_id=data.slots[slot_key].id,
                title=title,
                subject="Operating Systems",
                semester="Semester 3",
                audio_object_key=f"audio/{key}.mp3",
                audio_filename=f"{key}.mp3",
                audio_mime="audio/mpeg",
                duration_seconds=3600.0,
                chunk_count=2,
                status="ready",
                published=True,
                transcript=f"Full audio transcript for {title}. Exclusive details: {' '.join(concepts)}.",
                materials={
                    "summary": summary,
                    "key_concepts": concepts,
                    "key_topics": ["Operating Systems"],
                    "quiz": [
                        {
                            "question": f"What is the key mechanism in {title}?",
                            "options": [concepts[0], "Random guess", "None", "Other"],
                            "answer_index": 0,
                            "explanation": f"{concepts[0]} is foundational.",
                        }
                    ],
                },
                cheatsheet={"sections": [{"heading": "Summary", "points": concepts}]},
                podcast_script={"title": title, "script": f"Welcome to {title} podcast."},
                embedding=emb,
                created_at=now,
                updated_at=now,
            )
            session.add(lec)
            data.lectures[key] = lec
        await session.flush()

        await session.commit()
        return data

    except Exception:
        await session.rollback()
        raise
    finally:
        if close_session_on_exit:
            await session.close()
