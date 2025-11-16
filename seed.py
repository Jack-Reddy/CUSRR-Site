from models import db, User, Presentation
from csv_importer import import_users_from_csv


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

    # --- Presentations ---
    p1 = Presentation(
        title="If this presentation is showing something is broken",
        abstract=(
            "Artificial intelligence is rapidly transforming the landscape of learning and education, "
            "shaping how students, instructors, and institutions engage with knowledge. "
            "From personalized tutoring systems that adapt to individual learning styles, "
            "to intelligent content generation that supports creative exploration, AI is opening new possibilities for both teaching and learning. "
            "This presentation explores current applications of AI in educational settings, "
            "including adaptive learning platforms, automated assessment tools, and interactive learning environments. "
            "We also consider challenges such as ethical use, potential biases in AI algorithms, and the implications for educators and students alike. "
            "By examining case studies and ongoing research, participants will gain insight into how AI-driven tools can enhance learning outcomes, "
            "streamline administrative processes, and foster lifelong learning in increasingly digital classrooms."
        ),
        subject="Artificial Intelligence",
        time="2024-11-05 10:00",
        room="Room A",
        type="Blitz"
    )

    p2 = Presentation(
        title="Climate Change and Policy",
        abstract=(
            "Climate change represents one of the most pressing global challenges of the 21st century, "
            "with profound implications for ecosystems, human health, and economic stability. "
            "This presentation examines the complex interaction between climate science, environmental policy, and societal response. "
            "It reviews the latest research on greenhouse gas emissions, rising temperatures, and extreme weather events, "
            "while analyzing international policy frameworks aimed at mitigation and adaptation, such as the Paris Agreement. "
            "Participants will learn about the role of governmental and non-governmental actors in shaping policy, "
            "including regulatory measures, incentives for renewable energy, and community-based adaptation strategies. "
            "The discussion will also address economic considerations, social equity, and the ethical dimensions of climate action, "
            "highlighting how effective policy implementation is critical to reducing the human and environmental impacts of global warming."
        ),
        subject="Environmental Studies",
        time="2026-11-05 13:00",
        room="Room B",
        type="Poster"
    )

    p3 = Presentation(
        title="Modern Web Security",
        abstract=(
            "Web security has become a crucial concern as online applications increasingly store sensitive data and handle critical transactions. "
            "This presentation provides an in-depth look at contemporary best practices for securing web applications, "
            "covering both frontend and backend considerations. Topics include the implementation of secure authentication mechanisms, "
            "protection against common attacks such as SQL injection, cross-site scripting (XSS), and cross-site request forgery (CSRF), "
            "as well as the importance of secure data storage and encryption. "
            "We will also explore emerging security technologies, automated vulnerability scanning, and continuous monitoring practices. "
            "By analyzing real-world case studies, participants will understand the consequences of security breaches, "
            "as well as strategies for risk mitigation and proactive security management. "
            "This session emphasizes the critical role of developers, engineers, and organizations in creating resilient web environments."
        ),
        subject="Cybersecurity",
        time="2026-11-06 09:30",
        room="Room C",
        type="Presentation"
    )

    p4 = Presentation(
        title="Advances in Quantum Computing",
        abstract=(
            "Quantum computing represents a paradigm shift in computation, leveraging the principles of quantum mechanics to solve problems "
            "that are intractable for classical computers. This presentation explores recent breakthroughs in quantum algorithms, "
            "hardware development, and error correction techniques. Attendees will gain insight into how quantum bits, or qubits, allow for "
            "superposition and entanglement, enabling parallel computation on an unprecedented scale. "
            "Applications in cryptography, optimization, and simulation of complex physical systems will be discussed, "
            "alongside challenges such as decoherence and scalability. "
            "The presentation also examines current industry and academic research, including quantum supremacy experiments, "
            "and considers the future potential of quantum technologies to impact fields ranging from medicine to finance. "
            "Participants will leave with a comprehensive understanding of both the promise and the hurdles of quantum computing."
        ),
        subject="Computer Science",
        time="2026-11-06 11:00",
        room="Room D",
        type="Blitz"
    )

    p5 = Presentation(
        title="Renewable Energy Storage",
        abstract=(
            "As global energy demand grows and the shift to renewable sources accelerates, efficient energy storage has become a critical challenge. "
            "This presentation explores cutting-edge technologies for storing energy generated from solar, wind, and other renewable sources. "
            "We analyze battery systems, including lithium-ion and solid-state batteries, as well as emerging alternatives such as hydrogen storage, "
            "flow batteries, and supercapacitors. The session discusses efficiency, cost, scalability, and environmental impact, "
            "highlighting the advantages and limitations of each technology. Participants will also learn about integration with smart grids, "
            "energy management strategies, and real-world case studies demonstrating how effective storage solutions enable reliable renewable energy deployment. "
            "By understanding the latest advancements and ongoing research, attendees will gain insight into the technological and policy considerations "
            "that will shape the future of sustainable energy systems."
        ),
        subject="Energy Engineering",
        time="2026-11-06 14:00",
        room="Room E",
        type="Poster"
    )

    p6 = Presentation(
        title="Inclusive Design in Technology",
        abstract=(
            "Inclusive design ensures that technology is accessible and usable by as many people as possible, including those with disabilities, "
            "varied cultural backgrounds, and diverse abilities. This presentation examines the principles and practices of inclusive design "
            "in software development, web design, and user experience. Topics include accessibility standards, assistive technologies, "
            "user-centered design methodologies, and evaluation techniques to identify barriers. "
            "We will explore case studies of successful inclusive products, highlighting how incorporating diverse perspectives from the outset "
            "enhances usability, innovation, and social impact. Participants will also learn about the ethical and legal responsibilities of designers "
            "and developers to ensure equitable access. The session aims to provide actionable strategies for creating technology that empowers all users "
            "while improving overall user satisfaction and product adoption."
        ),
        subject="Human-Computer Interaction",
        time="2026-11-07 09:00",
        room="Room F",
        type="Presentation"
    )

    p7 = Presentation(
        title="Neuroscience of Decision Making",
        abstract=(
            "Understanding how humans make decisions is a central question in neuroscience, psychology, and behavioral economics. "
            "This presentation explores the brain mechanisms underlying decision-making processes, from evaluating options to predicting outcomes. "
            "We will discuss the role of neural circuits in reward processing, risk assessment, and emotional regulation, "
            "and examine experimental findings from neuroimaging, electrophysiology, and computational modeling studies. "
            "The session will highlight applications of this research in marketing, policy design, education, and clinical contexts, "
            "demonstrating how knowledge of cognitive and neural mechanisms can improve decision outcomes and mitigate biases. "
            "Participants will gain insight into interdisciplinary approaches that combine neuroscience, data analytics, and behavioral science "
            "to better understand and influence human behavior in both individual and organizational settings."
        ),
        subject="Neuroscience",
        time="2026-11-07 11:30",
        room="Room G",
        type="Blitz"
    )

    p8 = Presentation(
        title="Ethics of Artificial Intelligence",
        abstract=(
            "As AI systems become more powerful and pervasive, ethical considerations are increasingly important in guiding their development and use. "
            "This presentation examines philosophical, legal, and societal dimensions of AI ethics, including fairness, accountability, transparency, and privacy. "
            "We explore challenges such as algorithmic bias, surveillance, job displacement, and autonomous decision-making, "
            "and discuss strategies for responsible design and regulation. Case studies illustrate the consequences of ethical lapses in AI deployment, "
            "while highlighting approaches to mitigate harm and promote social good. Participants will engage with questions about AI governance, "
            "human-AI collaboration, and the balance between innovation and moral responsibility. "
            "The session emphasizes interdisciplinary perspectives, drawing from computer science, law, philosophy, and public policy, "
            "to equip attendees with a comprehensive framework for evaluating and implementing ethical AI practices."
        ),
        subject="Philosophy",
        time="2026-11-07 13:30",
        room="Room H",
        type="Presentation"
    )

    p9 = Presentation(
        title="Ocean Plastic Solutions",
        abstract=(
            "Plastic pollution is one of the most urgent environmental challenges, threatening marine ecosystems, wildlife, and human health. "
            "This presentation focuses on innovative strategies to reduce, recover, and repurpose plastic waste in oceans. "
            "Topics include policy initiatives, technological solutions for cleanup, biodegradable materials, and community-based recycling programs. "
            "We examine case studies demonstrating the effectiveness of large-scale interventions and grassroots initiatives, "
            "highlighting lessons learned and best practices. The session also addresses the environmental, economic, and social impacts of plastic pollution, "
            "and considers future trends in sustainable material design, circular economy approaches, and international collaboration. "
            "Participants will gain insight into how multi-disciplinary efforts can address complex environmental problems, "
            "and explore actionable steps to mitigate the global plastic crisis."
        ),
        subject="Marine Biology",
        time="2026-11-08 10:00",
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
