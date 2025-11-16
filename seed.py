from models import db, User, Presentation
from csv_importer import import_users_from_csv
from datetime import datetime

def setup_permissions():
    """Import permissions from a CSV file."""
    try:
        with open('permissions.csv', 'rb') as file:
            added, warnings = import_users_from_csv(file)
            print(f"Imported {added} users from permissions.csv")
            for warning in warnings:
                print(f"Warning: {warning}")
    except FileNotFoundError:
        print("permissions.csv file not found. Skipping permissions setup.")

def seed_data():
    """Populate the database with initial test data."""

    def parse_time(time_str):
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M")

    # --- Presentations ---
    p1 = Presentation(
        title="If this presentation is showing something is broken",
        abstract=(
            "Artificial intelligence is transforming learning and education, reshaping how students and instructors engage with knowledge. "
            "From adaptive tutoring systems to AI-generated content, technology is creating new ways to teach and learn. "
            "This presentation explores current AI applications in education, including automated assessment tools, interactive learning platforms, "
            "and personalized feedback systems. We discuss challenges like ethical use, potential biases, and implications for educators and students. "
            "Through case studies and research, participants will see how AI can enhance learning outcomes, streamline administrative tasks, "
            "and support lifelong learning in digital classrooms."
        ),
        subject="Artificial Intelligence",
        time=parse_time("2024-11-05 10:00"),
        room="Room A",
        type="Blitz"
    )

    p2 = Presentation(
        title="Climate Change and Policy",
        abstract=(
            "Climate change is one of the most pressing global challenges, affecting ecosystems, health, and economies. "
            "This session examines the intersection of climate science, policy, and societal response. "
            "We review research on emissions, rising temperatures, and extreme weather, and analyze international frameworks like the Paris Agreement. "
            "Participants will learn how governments and communities implement mitigation and adaptation strategies, including renewable energy incentives and local initiatives. "
            "Economic, social, and ethical considerations will be discussed, highlighting the importance of effective policy in reducing environmental and human impacts. "
            "Attendees will leave with a comprehensive understanding of the challenges and solutions in climate action, bridging science and policy."
        ),
        subject="Environmental Studies",
        time=parse_time("2026-11-05 13:00"),
        room="Room B",
        type="Poster"
    )

    p3 = Presentation(
        title="Modern Web Security",
        abstract=(
            "Web security is critical as applications store sensitive data and perform vital transactions online. "
            "This presentation covers best practices for securing web applications, including authentication, data encryption, and protection against attacks like SQL injection, XSS, and CSRF. "
            "We explore both frontend and backend security, emerging technologies, automated vulnerability scanning, and continuous monitoring. "
            "Real-world case studies illustrate the consequences of breaches and how organizations can mitigate risks. "
            "Attendees will understand proactive security measures, developer responsibilities, and strategies for creating resilient web environments."
        ),
        subject="Cybersecurity",
        time=parse_time("2026-11-06 09:30"),
        room="Room C",
        type="Presentation"
    )

    p4 = Presentation(
        title="Advances in Quantum Computing",
        abstract=(
            "Quantum computing leverages quantum mechanics to solve problems beyond classical computation. "
            "This session explores advances in algorithms, hardware, and error correction, showing how qubits enable parallel computation through superposition and entanglement. "
            "Applications in cryptography, optimization, and physical simulations are discussed, alongside challenges like decoherence and scalability. "
            "We review current academic and industry research, including quantum supremacy experiments, and assess the potential impact on fields from medicine to finance. "
            "Attendees will gain an understanding of both the promise and limitations of quantum technologies."
        ),
        subject="Computer Science",
        time=parse_time("2026-11-06 11:00"),
        room="Room D",
        type="Blitz"
    )

    p5 = Presentation(
        title="Renewable Energy Storage",
        abstract=(
            "Efficient energy storage is vital as the world shifts to renewable sources. "
            "This presentation examines technologies for storing solar, wind, and other renewable energy, including lithium-ion, solid-state, hydrogen, and flow batteries. "
            "We discuss efficiency, cost, scalability, environmental impact, and integration with smart grids. "
            "Real-world case studies demonstrate how storage solutions enable reliable renewable deployment. "
            "Attendees will learn about energy management strategies and the technological and policy considerations shaping the future of sustainable energy systems."
        ),
        subject="Energy Engineering",
        time=parse_time("2026-11-06 14:00"),
        room="Room E",
        type="Poster"
    )

    p6 = Presentation(
        title="Inclusive Design in Technology",
        abstract=(
            "Inclusive design ensures technology is accessible to all users, including those with disabilities and diverse backgrounds. "
            "This session covers principles and practices for inclusive software, web, and UX design, including accessibility standards and assistive technologies. "
            "We explore user-centered methodologies, barrier evaluation techniques, and case studies of successful inclusive products. "
            "Participants will learn ethical and legal responsibilities of designers and strategies to create technology that empowers everyone while improving usability and adoption."
        ),
        subject="Human-Computer Interaction",
        time=parse_time("2026-11-07 09:00"),
        room="Room F",
        type="Presentation"
    )

    p7 = Presentation(
        title="Neuroscience of Decision Making",
        abstract=(
            "Understanding human decision-making is central to neuroscience, psychology, and behavioral economics. "
            "This presentation explores neural mechanisms in evaluating options, predicting outcomes, and managing risk and emotion. "
            "We review neuroimaging, electrophysiology, and computational studies, and discuss applications in marketing, policy, education, and clinical contexts. "
            "Participants will see how combining neuroscience with behavioral science and data analytics improves decisions and reduces biases."
        ),
        subject="Neuroscience",
        time=parse_time("2026-11-07 11:30"),
        room="Room G",
        type="Blitz"
    )

    p8 = Presentation(
        title="Ethics of Artificial Intelligence",
        abstract=(
            "As AI becomes more pervasive, ethical considerations are critical. "
            "This session explores fairness, accountability, transparency, and privacy in AI systems, examining challenges like bias, surveillance, job displacement, and autonomous decisions. "
            "We discuss strategies for responsible AI design and governance, using case studies to highlight consequences of ethical lapses. "
            "Participants gain frameworks to evaluate and implement ethical AI practices across technology, law, and policy domains."
        ),
        subject="Philosophy",
        time=parse_time("2026-11-07 13:30"),
        room="Room H",
        type="Presentation"
    )

    p9 = Presentation(
        title="Ocean Plastic Solutions",
        abstract=(
            "Plastic pollution threatens marine ecosystems, wildlife, and human health. "
            "This presentation explores strategies to reduce, recover, and repurpose ocean plastic, including policies, cleanup technologies, biodegradable materials, and community recycling. "
            "Case studies demonstrate effectiveness of interventions, highlighting lessons learned and best practices. "
            "We also examine environmental, economic, and social impacts, and discuss future trends in circular economy and sustainable materials. "
            "Participants will gain insight into multi-disciplinary approaches to mitigate the global plastic crisis."
        ),
        subject="Marine Biology",
        time=parse_time("2026-11-08 10:00"),
        room="Room I",
        type="Poster"
    )

    db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p8, p9])
    db.session.commit()


    # --- Users ---
    users = [
        User(firstname="Alice", lastname="Johnson", email="alice@example.com", presentation_id=p1.id, activity="Speaker", auth="organizer"),
        User(firstname="Bob", lastname="Smith", email="bob@example.com", presentation_id=p1.id, activity="Co-presenter", auth="abstract grader"),
        User(firstname="Catherine", lastname="Lee", email="catherine@example.com", presentation_id=p2.id, activity="Moderator", auth="attendee"),
        User(firstname="Daniel", lastname="Patel", email="daniel@example.com", presentation_id=p3.id, activity="Instructor", auth="attendee"),
        User(firstname="Ella", lastname="Martinez", email="ella@example.com", presentation_id=p3.id, activity="Assistant", auth="attendee"),

        User(firstname="Frank", lastname="Nguyen", email="frank@example.com", presentation_id=p4.id, activity="Speaker"),
        User(firstname="Grace", lastname="Wong", email="grace@example.com", presentation_id=p4.id, activity="Researcher"),
        User(firstname="Hannah", lastname="Kim", email="hannah@example.com", presentation_id=p5.id, activity="Presenter"),
        User(firstname="Isaac", lastname="Reed", email="isaac@example.com", presentation_id=p5.id, activity="Assistant"),
        User(firstname="Jasmine", lastname="Brown", email="jasmine@example.com", presentation_id=p6.id, activity="Speaker"),

        User(firstname="Kevin", lastname="Lopez", email="kevin@example.com", presentation_id=p6.id, activity="Designer"),
        User(firstname="Laura", lastname="White", email="laura@example.com", presentation_id=p7.id, activity="Researcher"),
        User(firstname="Mason", lastname="Harris", email="mason@example.com", presentation_id=p8.id, activity="Lecturer"),
        User(firstname="Nina", lastname="Garcia", email="nina@example.com", presentation_id=p8.id, activity="Panelist"),
        User(firstname="Owen", lastname="Davis", email="owen@example.com", presentation_id=p9.id, activity="Coordinator"),
    ]

    db.session.add_all(users)
    db.session.commit()

    print("Database seeded with test data!")
