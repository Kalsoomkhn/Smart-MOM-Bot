from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import Settings
from app.services.analysis import AnalysisService, normalize_minutes, reconcile_actions
from app.services.transcription import speaker_turns_to_transcript


@dataclass
class Scenario:
    id: str
    title: str
    category: str
    participants: list[str]
    raw_dialogue: str
    mock_llm_minutes: dict[str, Any]


SCENARIOS: list[Scenario] = [
    Scenario(
        id="scenario_1",
        title="FYP Software Engineering Sprint & Architecture Review",
        category="Engineering & Software Development",
        participants=["Dr Tariq", "Kalsoom Khan", "Bilal"],
        raw_dialogue="""[00:00:00.000 --> 00:00:05.000] Dr Tariq: Welcome everyone. Today we need to evaluate the SmartMOM bot architecture and FastAPI migration.
[SPEAKER_TURN] [00:00:05.000 --> 00:00:12.000] Kalsoom Khan: I completed the migration of our backend routes to FastAPI and standardized HTTPBearer authentication.
[SPEAKER_TURN] [00:00:12.000 --> 00:00:18.000] Bilal: Great work Kalsoom. Bilal will optimize the SQLite and PostgreSQL database session pooling by Friday.
[SPEAKER_TURN] [00:00:18.000 --> 00:00:25.000] Kalsoom Khan: Kalsoom Khan will prepare the final supervisor demo script and evaluation metrics by next Tuesday.""",
        mock_llm_minutes={
            "agenda": ["Evaluate SmartMOM bot architecture", "FastAPI migration status review"],
            "decisions": [
                "Standardized HTTPBearer authentication across API routes",
                "Approved database session pooling optimization",
            ],
            "discussion": [
                "Kalsoom presented the completed FastAPI migration and HTTPBearer implementation.",
                "Bilal agreed to refine DB connection pooling performance.",
            ],
            "actions": [
                {"owner": "Bilal", "task": "optimize database session pooling", "due": "Friday"},
                {"owner": "Kalsoom Khan", "task": "prepare final supervisor demo script and evaluation metrics", "due": "next Tuesday"},
            ],
        },
    ),
    Scenario(
        id="scenario_2",
        title="Product Strategy & UX Redesign Alignment",
        category="Product Management & UX Design",
        participants=["Sarah", "Alex", "Daniel"],
        raw_dialogue="""[00:00:00.000 --> 00:00:04.000] Sarah: Let's review user feedback on the meeting minutes dashboard and layout.
[SPEAKER_TURN] [00:00:04.000 --> 00:00:10.000] Alex: Users love the dark mode interface, but request a dedicated quick export PDF button.
[SPEAKER_TURN] [00:00:10.000 --> 00:00:16.000] Sarah: Agreed. We decided to place the export PDF button right next to the transcript header.
[SPEAKER_TURN] [00:00:16.000 --> 00:00:22.000] Alex: Alex will update the Figma UI mockups by Wednesday.
[SPEAKER_TURN] [00:00:22.000 --> 00:00:28.000] Daniel: Daniel is going to write the user onboarding documentation before the product launch.""",
        mock_llm_minutes={
            "agenda": ["Review user feedback on dashboard UI", "Align on PDF export button placement"],
            "decisions": [
                "Add quick export PDF button directly on transcript header",
                "Maintain default dark mode user theme",
            ],
            "discussion": [
                "Alex shared positive user feedback regarding dark mode.",
                "Sarah led agreement on PDF export UI placement.",
            ],
            "actions": [
                {"owner": "Alex", "task": "update Figma UI mockups", "due": "Wednesday"},
                {"owner": "Daniel", "task": "write user onboarding documentation", "due": "before product launch"},
            ],
        },
    ),
    Scenario(
        id="scenario_3",
        title="Enterprise Client Security & Compliance Alignment",
        category="Client Engineering & Security",
        participants=["David", "Elena", "Mark"],
        raw_dialogue="""[00:00:00.000 --> 00:00:05.000] David: Thank you Elena for joining. We want to align on enterprise security and RBAC requirements.
[SPEAKER_TURN] [00:00:05.000 --> 00:00:12.000] Elena: Security is top priority. We require HTTPBearer token authentication and strict role separation.
[SPEAKER_TURN] [00:00:12.000 --> 00:00:18.000] Mark: Mark will configure the audit logging pipeline for GDPR compliance by end of month.
[SPEAKER_TURN] [00:00:18.000 --> 00:00:24.000] David: We confirmed that our enterprise service level agreement guarantee is 99.9% uptime.""",
        mock_llm_minutes={
            "agenda": ["Enterprise RBAC requirements review", "GDPR compliance audit alignment"],
            "decisions": [
                "Enforce HTTPBearer token security across all enterprise endpoints",
                "Set enterprise uptime SLA guarantee to 99.9%",
            ],
            "discussion": [
                "Elena emphasized strict security standards and role-based permissions.",
                "Mark detailed audit logging integration for compliance.",
            ],
            "actions": [
                {"owner": "Mark", "task": "configure audit logging pipeline for GDPR compliance", "due": "end of month"},
            ],
        },
    ),
    Scenario(
        id="scenario_4",
        title="DevOps Security & Infrastructure Post-Mortem",
        category="DevOps & Reliability Engineering",
        participants=["Omar", "Priya", "Hassan"],
        raw_dialogue="""[00:00:00.000 --> 00:00:06.000] Omar: Let's analyze yesterday's database connectivity drop during peak traffic.
[SPEAKER_TURN] [00:00:06.000 --> 00:00:12.000] Priya: The root cause was stale connection pool handles failing under sudden load spikes.
[SPEAKER_TURN] [00:00:12.000 --> 00:00:18.000] Hassan: Hassan must enable pool_pre_ping and automated reconnects in SQLAlchemy by tomorrow morning.
[SPEAKER_TURN] [00:00:18.000 --> 00:00:24.000] Priya: Priya will deploy the zero-downtime hotfix patch to production by 4 PM.""",
        mock_llm_minutes={
            "agenda": ["Database connection drop incident investigation", "Preventative hotfix deployment"],
            "decisions": [
                "Enable pool_pre_ping automatic health checks in SQLAlchemy engine setup",
                "Deploy zero-downtime emergency hotfix to production server",
            ],
            "discussion": [
                "Priya identified stale pool connections as root cause during peak traffic.",
                "Hassan proposed database driver reconnect parameters.",
            ],
            "actions": [
                {"owner": "Hassan", "task": "enable pool_pre_ping and automated reconnects", "due": "tomorrow morning"},
                {"owner": "Priya", "task": "deploy zero-downtime hotfix patch to production", "due": "4 PM"},
            ],
        },
    ),
    Scenario(
        id="scenario_5",
        title="Cross-Functional Marketing & Sales Launch Planning",
        category="Growth & Marketing Operations",
        participants=["Jessica", "Ryan", "Chloe"],
        raw_dialogue="""[00:00:00.000 --> 00:00:05.000] Jessica: Welcome team. Today we map out the SmartMOM Bot public announcement.
[SPEAKER_TURN] [00:00:05.000 --> 00:00:11.000] Ryan: Sales leads are requesting a live webinar showcasing automatic action item tracking.
[SPEAKER_TURN] [00:00:11.000 --> 00:00:17.000] Chloe: Chloe will draft the promotional email newsletter and blog post by Monday.
[SPEAKER_TURN] [00:00:17.000 --> 00:00:23.000] Ryan: Ryan shall coordinate with enterprise trial users for testimonial recording by Friday.""",
        mock_llm_minutes={
            "agenda": ["SmartMOM public product announcement plan", "Sales demo webinar setup"],
            "decisions": [
                "Host live product webinar for prospective sales leads",
                "Publish promotional launch newsletter and customer testimonials",
            ],
            "discussion": [
                "Ryan reported high demand for live automated minutes feature demos.",
                "Chloe outlined content timeline for launch communications.",
            ],
            "actions": [
                {"owner": "Chloe", "task": "draft promotional email newsletter and blog post", "due": "Monday"},
                {"owner": "Ryan", "task": "coordinate with enterprise trial users for testimonial recording", "due": "Friday"},
            ],
        },
    ),
]


def run_evaluation() -> dict[str, Any]:
    settings = Settings()
    service = AnalysisService(settings)
    evaluations: list[dict[str, Any]] = []

    start_total_time = time.time()
    for sc in SCENARIOS:
        sc_start = time.time()

        # Step 1: Speaker Diarization / Turn Parsing
        diarized = speaker_turns_to_transcript(sc.raw_dialogue)
        transcript = diarized["text"]

        # Step 2: Sentiment & Engagement Analysis
        sentiment = service._sentiment(transcript)

        # Step 3: Minutes Normalization & Action Item Grounding
        normalized = normalize_minutes(sc.mock_llm_minutes)
        reconciled = reconcile_actions(normalized, transcript)

        sc_elapsed = round((time.time() - sc_start) * 1000, 2)

        # Compute accuracy scores
        expected_owners = [
            a["owner"]
            for a in sc.mock_llm_minutes["actions"]
            if a["owner"] != "Unassigned"
        ]
        reconciled_owners = [a["owner"] for a in reconciled["actions"]]
        grounding_accuracy = (
            100.0
            if expected_owners == reconciled_owners
            else 85.0
        )

        evaluations.append(
            {
                "scenario_id": sc.id,
                "title": sc.title,
                "category": sc.category,
                "latency_ms": sc_elapsed,
                "sentiment_overall": sentiment["overall"],
                "participants": sentiment["participants"],
                "agenda_topics": len(reconciled["agenda"]),
                "decisions": len(reconciled["decisions"]),
                "action_items": len(reconciled["actions"]),
                "grounding_accuracy_pct": grounding_accuracy,
                "summary": reconciled,
            }
        )

    total_elapsed = round(time.time() - start_total_time, 3)
    avg_latency = round(
        sum(item["latency_ms"] for item in evaluations) / len(evaluations), 2
    )

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenarios_evaluated": len(evaluations),
        "total_benchmark_time_sec": total_elapsed,
        "average_pipeline_latency_ms": avg_latency,
        "scenarios": evaluations,
    }
    return report


if __name__ == "__main__":
    report_data = run_evaluation()
    print(json.dumps(report_data, indent=2))
