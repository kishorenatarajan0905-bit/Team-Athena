import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models import Course, ExperienceLevel
from app.services.embeddings import embed_course, build_course_text
from app.core.security import get_password_hash
from app.models import User, LearnerProfile
import structlog

logger = structlog.get_logger()


COURSES = [
    # Python / Data Science Track
    {
        "title": "Python Programming Fundamentals",
        "description": "Learn Python from scratch including variables, control structures, functions, data structures, and basic OOP concepts. Hands-on exercises with real-world examples.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 20,
        "prerequisites": [],
        "skills_covered": ["Python", "Programming Fundamentals", "Data Structures", "Functions"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "Data Analysis with Pandas",
        "description": "Master pandas for data manipulation, cleaning, aggregation, and visualization. Work with real datasets from various domains.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 15,
        "prerequisites": [],  # Will be set after course creation
        "skills_covered": ["Pandas", "Data Cleaning", "Data Visualization", "Exploratory Data Analysis"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "NumPy for Numerical Computing",
        "description": "Learn NumPy arrays, vectorized operations, broadcasting, and performance optimization for scientific computing.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 12,
        "prerequisites": [],
        "skills_covered": ["NumPy", "Arrays", "Vectorization", "Scientific Computing"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },
    {
        "title": "SQL for Data Science",
        "description": "Learn SQL queries, joins, subqueries, window functions, and database design for data analysis.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 18,
        "prerequisites": [],
        "skills_covered": ["SQL", "Database Queries", "Joins", "Window Functions"],
        "provider": "InPlant Academy",
        "rating": 4.9,
    },
    {
        "title": "Data Visualization with Matplotlib & Seaborn",
        "description": "Create publication-quality visualizations for exploratory analysis and presentations.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 10,
        "prerequisites": [],
        "skills_covered": ["Matplotlib", "Seaborn", "Data Visualization", "Plotting"],
        "provider": "InPlant Academy",
        "rating": 4.5,
    },
    {
        "title": "Machine Learning Foundations",
        "description": "Introduction to supervised and unsupervised learning, model evaluation, feature engineering, and scikit-learn.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 25,
        "prerequisites": [],
        "skills_covered": ["Machine Learning", "scikit-learn", "Supervised Learning", "Unsupervised Learning", "Model Evaluation"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "Deep Learning with PyTorch",
        "description": "Build neural networks from scratch using PyTorch. Cover CNNs, RNNs, transfer learning, and modern architectures.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 30,
        "prerequisites": [],
        "skills_covered": ["PyTorch", "Neural Networks", "CNNs", "RNNs", "Transfer Learning"],
        "provider": "InPlant Academy",
        "rating": 4.9,
    },
    {
        "title": "MLOps Fundamentals",
        "description": "Learn ML model deployment, monitoring, CI/CD for ML, feature stores, and model versioning with MLflow.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 20,
        "prerequisites": [],
        "skills_covered": ["MLOps", "MLflow", "Model Deployment", "Monitoring", "CI/CD"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },
    {
        "title": "Transformers & Large Language Models",
        "description": "Understand transformer architecture, BERT, GPT, fine-tuning, RAG, and building LLM applications.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 25,
        "prerequisites": [],
        "skills_covered": ["Transformers", "LLMs", "BERT", "GPT", "Fine-tuning", "RAG"],
        "provider": "InPlant Academy",
        "rating": 4.9,
    },
    {
        "title": "Computer Vision with OpenCV",
        "description": "Image processing, object detection, segmentation, and real-time video analysis with OpenCV and deep learning.",
        "domain": "Data Science",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 22,
        "prerequisites": [],
        "skills_covered": ["OpenCV", "Computer Vision", "Image Processing", "Object Detection"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },

    # Web Development Track
    {
        "title": "HTML & CSS Fundamentals",
        "description": "Build responsive web pages with semantic HTML5, modern CSS3, Flexbox, Grid, and animations.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 15,
        "prerequisites": [],
        "skills_covered": ["HTML", "CSS", "Flexbox", "Grid", "Responsive Design"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "JavaScript Essentials",
        "description": "Modern JavaScript (ES6+): variables, functions, async/await, DOM manipulation, modules, and tooling.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 20,
        "prerequisites": [],
        "skills_covered": ["JavaScript", "ES6+", "Async Programming", "DOM", "Modules"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "TypeScript for JavaScript Developers",
        "description": "Add static typing to JavaScript. Learn types, interfaces, generics, utility types, and configuration.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 12,
        "prerequisites": [],
        "skills_covered": ["TypeScript", "Static Typing", "Generics", "Type Safety"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "React Fundamentals",
        "description": "Build component-based UIs with React: hooks, state management, context, routing, and best practices.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 25,
        "prerequisites": [],
        "skills_covered": ["React", "Hooks", "State Management", "Context API", "React Router"],
        "provider": "InPlant Academy",
        "rating": 4.9,
    },
    {
        "title": "Next.js Full-Stack Development",
        "description": "Build full-stack applications with Next.js 14: App Router, Server Components, API routes, authentication, and deployment.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 28,
        "prerequisites": [],
        "skills_covered": ["Next.js", "Server Components", "Full-Stack", "Authentication", "Deployment"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "Node.js & Express Backend Development",
        "description": "Build RESTful APIs with Node.js, Express, middleware, authentication, validation, and database integration.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 22,
        "prerequisites": [],
        "skills_covered": ["Node.js", "Express", "REST APIs", "Authentication", "Middleware"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },
    {
        "title": "GraphQL API Development",
        "description": "Design and implement GraphQL schemas, resolvers, subscriptions, and federation with Apollo Server.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 18,
        "prerequisites": [],
        "skills_covered": ["GraphQL", "Apollo Server", "Schema Design", "Resolvers", "Federation"],
        "provider": "InPlant Academy",
        "rating": 4.5,
    },
    {
        "title": "Testing React Applications",
        "description": "Unit, integration, and E2E testing with Jest, React Testing Library, and Cypress.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 15,
        "prerequisites": [],
        "skills_covered": ["Jest", "React Testing Library", "Cypress", "Unit Testing", "E2E Testing"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "Web Performance Optimization",
        "description": "Optimize Core Web Vitals, lazy loading, code splitting, caching strategies, and bundle analysis.",
        "domain": "Web Development",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 12,
        "prerequisites": [],
        "skills_covered": ["Performance", "Core Web Vitals", "Lazy Loading", "Caching", "Bundle Analysis"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },

    # DevOps / Cloud Track
    {
        "title": "Linux Command Line Mastery",
        "description": "Essential Linux skills: file system, permissions, processes, networking, shell scripting, and package management.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 15,
        "prerequisites": [],
        "skills_covered": ["Linux", "Shell Scripting", "CLI", "Permissions", "Process Management"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "Docker Fundamentals",
        "description": "Containerize applications with Docker: images, containers, volumes, networks, Docker Compose, and multi-stage builds.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 18,
        "prerequisites": [],
        "skills_covered": ["Docker", "Containers", "Docker Compose", "Multi-stage Builds", "Images"],
        "provider": "InPlant Academy",
        "rating": 4.9,
    },
    {
        "title": "Kubernetes Essentials",
        "description": "Deploy and manage containerized applications on Kubernetes: pods, services, deployments, configmaps, secrets, and ingress.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 25,
        "prerequisites": [],
        "skills_covered": ["Kubernetes", "Pods", "Services", "Deployments", "Helm", "Ingress"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "AWS Cloud Practitioner",
        "description": "Core AWS services: EC2, S3, RDS, Lambda, IAM, VPC, CloudFormation, and cost optimization.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 20,
        "prerequisites": [],
        "skills_covered": ["AWS", "EC2", "S3", "Lambda", "IAM", "VPC", "CloudFormation"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "CI/CD with GitHub Actions",
        "description": "Automate build, test, and deployment pipelines with GitHub Actions: workflows, matrices, secrets, and environments.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 15,
        "prerequisites": [],
        "skills_covered": ["GitHub Actions", "CI/CD", "Pipelines", "Automation", "Deployment"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "Infrastructure as Code with Terraform",
        "description": "Provision and manage cloud infrastructure declaratively with Terraform: modules, state, providers, and best practices.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 18,
        "prerequisites": [],
        "skills_covered": ["Terraform", "IaC", "Modules", "State Management", "Providers"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "Monitoring & Observability",
        "description": "Implement comprehensive monitoring with Prometheus, Grafana, Loki, and distributed tracing with Jaeger.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 20,
        "prerequisites": [],
        "skills_covered": ["Prometheus", "Grafana", "Loki", "Jaeger", "Observability", "Alerting"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },
    {
        "title": "GitOps with ArgoCD",
        "description": "Implement GitOps workflows for Kubernetes: ArgoCD, application sync, progressive delivery, and multi-cluster management.",
        "domain": "DevOps",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 15,
        "prerequisites": [],
        "skills_covered": ["ArgoCD", "GitOps", "Progressive Delivery", "Multi-cluster", "Sync"],
        "provider": "InPlant Academy",
        "rating": 4.5,
    },

    # Mobile Development Track
    {
        "title": "React Native Fundamentals",
        "description": "Build cross-platform mobile apps with React Native: components, navigation, state management, and native modules.",
        "domain": "Mobile Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 25,
        "prerequisites": [],
        "skills_covered": ["React Native", "Mobile Development", "Navigation", "Expo", "Native Modules"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "Flutter & Dart Development",
        "description": "Build beautiful native apps with Flutter: widgets, state management, animations, platform integration, and testing.",
        "domain": "Mobile Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 28,
        "prerequisites": [],
        "skills_covered": ["Flutter", "Dart", "Widgets", "State Management", "Animations"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "iOS Development with Swift",
        "description": "Native iOS development with SwiftUI: views, data flow, persistence, networking, and App Store deployment.",
        "domain": "Mobile Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 30,
        "prerequisites": [],
        "skills_covered": ["Swift", "SwiftUI", "iOS", "Core Data", "Networking", "App Store"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },
    {
        "title": "Android Development with Kotlin",
        "description": "Modern Android development with Jetpack Compose: UI, architecture, Coroutines, Room, and Play Store deployment.",
        "domain": "Mobile Development",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 30,
        "prerequisites": [],
        "skills_covered": ["Kotlin", "Jetpack Compose", "Android", "Coroutines", "Room", "Play Store"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },

    # Cybersecurity Track
    {
        "title": "Cybersecurity Fundamentals",
        "description": "Core security concepts: CIA triad, threat modeling, network security, cryptography basics, and security frameworks.",
        "domain": "Cybersecurity",
        "difficulty": ExperienceLevel.BEGINNER,
        "duration_hours": 18,
        "prerequisites": [],
        "skills_covered": ["Security Fundamentals", "Threat Modeling", "Cryptography", "Network Security", "Frameworks"],
        "provider": "InPlant Academy",
        "rating": 4.8,
    },
    {
        "title": "Ethical Hacking & Penetration Testing",
        "description": "Learn penetration testing methodology: reconnaissance, scanning, exploitation, post-exploitation, and reporting.",
        "domain": "Cybersecurity",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 30,
        "prerequisites": [],
        "skills_covered": ["Penetration Testing", "Reconnaissance", "Exploitation", "Burp Suite", "Metasploit"],
        "provider": "InPlant Academy",
        "rating": 4.9,
    },
    {
        "title": "Application Security & Secure Coding",
        "description": "OWASP Top 10, secure coding practices, code review, SAST/DAST, and DevSecOps integration.",
        "domain": "Cybersecurity",
        "difficulty": ExperienceLevel.INTERMEDIATE,
        "duration_hours": 20,
        "prerequisites": [],
        "skills_covered": ["OWASP", "Secure Coding", "SAST", "DAST", "DevSecOps", "Code Review"],
        "provider": "InPlant Academy",
        "rating": 4.7,
    },
    {
        "title": "Cloud Security Architecture",
        "description": "Secure cloud environments: identity management, network security, data protection, compliance, and incident response.",
        "domain": "Cybersecurity",
        "difficulty": ExperienceLevel.ADVANCED,
        "duration_hours": 25,
        "prerequisites": [],
        "skills_covered": ["Cloud Security", "IAM", "Network Security", "Compliance", "Incident Response"],
        "provider": "InPlant Academy",
        "rating": 4.6,
    },
]


async def seed_courses(db: AsyncSession):
    """Seed courses and generate embeddings."""
    logger.info("seeding_courses", count=len(COURSES))

    # First pass: create courses without prerequisites
    course_objects = {}
    for course_data in COURSES:
        course = Course(**course_data)
        db.add(course)
        course_objects[course_data["title"]] = course

    await db.flush()

    # Set prerequisites by title mapping
    prerequisite_map = {
        "Data Analysis with Pandas": ["Python Programming Fundamentals"],
        "NumPy for Numerical Computing": ["Python Programming Fundamentals"],
        "Machine Learning Foundations": ["Data Analysis with Pandas", "NumPy for Numerical Computing"],
        "Deep Learning with PyTorch": ["Machine Learning Foundations"],
        "MLOps Fundamentals": ["Machine Learning Foundations", "Docker Fundamentals"],
        "Transformers & Large Language Models": ["Deep Learning with PyTorch"],
        "Computer Vision with OpenCV": ["Deep Learning with PyTorch", "NumPy for Numerical Computing"],
        "TypeScript for JavaScript Developers": ["JavaScript Essentials"],
        "React Fundamentals": ["JavaScript Essentials", "HTML & CSS Fundamentals"],
        "Next.js Full-Stack Development": ["React Fundamentals", "TypeScript for JavaScript Developers", "Node.js & Express Backend Development"],
        "GraphQL API Development": ["Node.js & Express Backend Development", "TypeScript for JavaScript Developers"],
        "Testing React Applications": ["React Fundamentals"],
        "Web Performance Optimization": ["React Fundamentals", "Next.js Full-Stack Development"],
        "Kubernetes Essentials": ["Docker Fundamentals", "Linux Command Line Mastery"],
        "CI/CD with GitHub Actions": ["Docker Fundamentals", "Linux Command Line Mastery"],
        "Infrastructure as Code with Terraform": ["AWS Cloud Practitioner", "Linux Command Line Mastery"],
        "Monitoring & Observability": ["Kubernetes Essentials", "Docker Fundamentals"],
        "GitOps with ArgoCD": ["Kubernetes Essentials", "CI/CD with GitHub Actions"],
        "React Native Fundamentals": ["React Fundamentals", "JavaScript Essentials"],
        "Flutter & Dart Development": ["JavaScript Essentials"],  # Basic programming knowledge
        "iOS Development with Swift": ["JavaScript Essentials"],  # Basic programming knowledge
        "Android Development with Kotlin": ["JavaScript Essentials"],  # Basic programming knowledge
        "Ethical Hacking & Penetration Testing": ["Cybersecurity Fundamentals", "Linux Command Line Mastery"],
        "Application Security & Secure Coding": ["Cybersecurity Fundamentals", "JavaScript Essentials"],
        "Cloud Security Architecture": ["AWS Cloud Practitioner", "Cybersecurity Fundamentals"],
    }

    # Second pass: update prerequisites
    for course_title, prereq_titles in prerequisite_map.items():
        course = course_objects.get(course_title)
        if course:
            prereq_ids = [course_objects[t].id for t in prereq_titles if t in course_objects]
            course.prerequisites = prereq_ids

    await db.commit()

    # Third pass: generate embeddings
    logger.info("generating_embeddings")
    courses_to_embed = list(course_objects.values())
    for i, course in enumerate(courses_to_embed):
        try:
            text = build_course_text(course)
            # We'll embed in batch later for efficiency
            logger.debug("embedding_course", title=course.title, index=i)
        except Exception as e:
            logger.warning("embedding_failed", title=course.title, error=str(e))

    # Batch embed all courses
    try:
        from app.services.embeddings import get_embeddings
        texts = [build_course_text(c) for c in courses_to_embed]
        embeddings = await get_embeddings(texts)
        for course, embedding in zip(courses_to_embed, embeddings):
            course.embedding = embedding
        await db.commit()
        logger.info("embeddings_generated", count=len(embeddings))
    except Exception as e:
        logger.error("batch_embedding_failed", error=str(e))

    return course_objects


async def create_demo_user(db: AsyncSession) -> User:
    """Create a demo user for testing."""
    email = "demo@inplant.ai"
    result = await db.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash("demo1234"),
            name="Demo Learner",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create profile with some interests
        profile = LearnerProfile(
            user_id=user.id,
            interests=["Python", "Machine Learning", "Data Science", "AI"],
            experience_level=ExperienceLevel.BEGINNER,
            goals="I want to become a machine learning engineer and build AI-powered applications. I have basic programming knowledge and want to learn the full stack from data processing to model deployment.",
            target_role="Machine Learning Engineer",
            time_commitment_hours=15,
            learning_style="project-based",
        )
        db.add(profile)
        await db.commit()

        # Generate profile embedding
        from app.services.embeddings import embed_profile
        try:
            profile.skill_embedding = await embed_profile(profile)
            await db.commit()
        except Exception as e:
            logger.warning("demo_profile_embedding_failed", error=str(e))

    return user


async def main():
    engine = create_async_engine(settings.database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        try:
            await seed_courses(db)
            await create_demo_user(db)
            logger.info("seeding_completed")
        except Exception as e:
            logger.error("seeding_failed", error=str(e))
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())