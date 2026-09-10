import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# Page dimensions for A4: 595.27 x 841.89 points
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 42
USABLE_WIDTH = PAGE_WIDTH - (2 * MARGIN)  # ~511 pt

def create_api_docs_pdf(output_paths: list[Path]):
    styles = getSampleStyleSheet()
    
    # Custom Palette
    C_PRIMARY = colors.HexColor("#1E3A8A")     # Deep Navy
    C_SECONDARY = colors.HexColor("#2563EB")   # Blue Accent
    C_DARK = colors.HexColor("#0F172A")        # Slate 900
    C_TEXT = colors.HexColor("#334155")        # Slate 700
    C_MUTED = colors.HexColor("#64748B")       # Slate 500
    C_LIGHT = colors.HexColor("#F8FAFC")       # Slate 50
    C_BORDER = colors.HexColor("#CBD5E1")      # Slate 300
    C_SUCCESS = colors.HexColor("#059669")     # Emerald
    C_WARNING = colors.HexColor("#D97706")     # Amber
    C_DANGER = colors.HexColor("#DC2626")      # Red
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=C_PRIMARY,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=C_MUTED,
        spaceAfter=14
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=C_PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=C_DARK,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=C_TEXT,
        spaceAfter=5
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )
    
    badge_get = ParagraphStyle('BadgeGet', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=C_SUCCESS)
    badge_post = ParagraphStyle('BadgePost', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=C_SECONDARY)
    badge_put = ParagraphStyle('BadgePut', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=C_WARNING)
    badge_delete = ParagraphStyle('BadgeDelete', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=C_DANGER)
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3
    )

    tbl_header = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.white)
    tbl_cell = ParagraphStyle('TblCell', fontName='Helvetica', fontSize=8, leading=11, textColor=C_TEXT)
    tbl_cell_bold = ParagraphStyle('TblCellBold', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=C_DARK)
    tbl_code = ParagraphStyle('TblCode', fontName='Courier', fontSize=7.5, leading=10, textColor=C_PRIMARY)

    story = []

    # -------------------------------------------------------------
    # Cover / Header Banner
    # -------------------------------------------------------------
    story.append(Paragraph("SmartMOM Bot — API Reference & Integration Guide", title_style))
    story.append(Paragraph("A Complete Guide to Endpoint Lifecycles, Call Ordering, Specifications & Request/Response Contracts", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_SECONDARY, spaceBefore=0, spaceAfter=10))

    meta_table_data = [
        [
            Paragraph("<b>Project:</b> SmartMOM Bot (Meeting Intelligence Workspace)", meta_style),
            Paragraph("<b>Backend Stack:</b> FastAPI, SQLAlchemy, SQLite/PostgreSQL", meta_style),
        ],
        [
            Paragraph("<b>Auth Protocol:</b> JWT Bearer Token (Authorization Header)", meta_style),
            Paragraph("<b>Core AI:</b> Local Whisper CPP, Quantized Qwen2.5, DistilBERT", meta_style),
        ],
        [
            Paragraph("<b>Base URL:</b> <code>/api</code> (Proxied via Nginx / Vite)", meta_style),
            Paragraph("<b>Document Version:</b> 1.0.0 (Production Verified)", meta_style),
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[USABLE_WIDTH * 0.52, USABLE_WIDTH * 0.48])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # Section 1: Execution Order & Lifecycle Workflow
    # -------------------------------------------------------------
    story.append(Paragraph("1. Recommended Endpoint Execution Sequence", h1_style))
    story.append(Paragraph(
        "To achieve a complete automated meeting lifecycle—from raw spoken audio to verified, downloadable minutes and analytics—endpoints should be executed in the exact ordered sequence detailed below:",
        body_style
    ))

    order_data = [
        [
            Paragraph("<b>Step</b>", tbl_header),
            Paragraph("<b>Endpoint & Method</b>", tbl_header),
            Paragraph("<b>Lifecycle Phase</b>", tbl_header),
            Paragraph("<b>Meeting Status</b>", tbl_header),
            Paragraph("<b>Role Required</b>", tbl_header)
        ],
        [
            Paragraph("<b>0</b>", tbl_cell_bold),
            Paragraph("<font color='#059669'><b>GET</b></font> /health", tbl_code),
            Paragraph("System Pre-flight check", tbl_cell),
            Paragraph("N/A", tbl_cell),
            Paragraph("Public", tbl_cell)
        ],
        [
            Paragraph("<b>1</b>", tbl_cell_bold),
            Paragraph("<font color='#2563EB'><b>POST</b></font> /api/auth/register<br/>or /api/auth/login", tbl_code),
            Paragraph("Authentication & JWT retrieval", tbl_cell),
            Paragraph("N/A", tbl_cell),
            Paragraph("Public", tbl_cell)
        ],
        [
            Paragraph("<b>2</b>", tbl_cell_bold),
            Paragraph("<font color='#059669'><b>GET</b></font> /api/auth/me", tbl_code),
            Paragraph("Session validation & profile load", tbl_cell),
            Paragraph("N/A", tbl_cell),
            Paragraph("Authenticated", tbl_cell)
        ],
        [
            Paragraph("<b>3</b>", tbl_cell_bold),
            Paragraph("<font color='#2563EB'><b>POST</b></font> /api/meetings", tbl_code),
            Paragraph("Upload audio recording", tbl_cell),
            Paragraph("<code>uploaded</code>", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ],
        [
            Paragraph("<b>4</b>", tbl_cell_bold),
            Paragraph("<font color='#2563EB'><b>POST</b></font> /api/meetings/{id}/participants", tbl_code),
            Paragraph("Invite registered participants", tbl_cell),
            Paragraph("<code>uploaded</code>", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ],
        [
            Paragraph("<b>5</b>", tbl_cell_bold),
            Paragraph("<font color='#2563EB'><b>POST</b></font> /api/meetings/{id}/transcribe", tbl_code),
            Paragraph("Whisper Speech-to-Text extraction", tbl_cell),
            Paragraph("<code>transcribing</code><br/>→ <code>transcribed</code>", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ],
        [
            Paragraph("<b>5a</b>", tbl_cell_bold),
            Paragraph("<font color='#D97706'><b>PUT</b></font> /api/meetings/{id}/transcript", tbl_code),
            Paragraph("Optional manual transcript edits", tbl_cell),
            Paragraph("<code>transcribed</code>", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ],
        [
            Paragraph("<b>6</b>", tbl_cell_bold),
            Paragraph("<font color='#2563EB'><b>POST</b></font> /api/meetings/{id}/analyze", tbl_code),
            Paragraph("AI Minutes & Sentiment Analysis", tbl_cell),
            Paragraph("<code>ready</code>", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ],
        [
            Paragraph("<b>6a</b>", tbl_cell_bold),
            Paragraph("<font color='#D97706'><b>PUT</b></font> /api/meetings/{id}/summary", tbl_code),
            Paragraph("Human review & edits (versioned)", tbl_cell),
            Paragraph("<code>saved</code>", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ],
        [
            Paragraph("<b>7</b>", tbl_cell_bold),
            Paragraph("<font color='#059669'><b>GET</b></font> /api/meetings/{id}/export.pdf", tbl_code),
            Paragraph("Download formal PDF minutes", tbl_cell),
            Paragraph("<code>ready</code> / <code>saved</code>", tbl_cell),
            Paragraph("All Members", tbl_cell)
        ],
        [
            Paragraph("<b>8</b>", tbl_cell_bold),
            Paragraph("<font color='#2563EB'><b>POST</b></font> /api/meetings/{id}/feedback", tbl_code),
            Paragraph("Submit 1–5 star rating & feedback", tbl_cell),
            Paragraph("<code>ready</code> / <code>saved</code>", tbl_cell),
            Paragraph("All Members", tbl_cell)
        ],
        [
            Paragraph("<b>9</b>", tbl_cell_bold),
            Paragraph("<font color='#DC2626'><b>DELETE</b></font> /api/meetings/{id}", tbl_code),
            Paragraph("Permanent cleanup & file deletion", tbl_cell),
            Paragraph("Deleted", tbl_cell),
            Paragraph("Organizer", tbl_cell)
        ]
    ]

    t_order = Table(order_data, colWidths=[32, 175, 140, 84, 80])
    t_order.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_order)
    story.append(Spacer(1, 10))

    # Narrative explanation of ordering logic
    story.append(Paragraph(
        "<b>Why this order matters:</b><br/>"
        "• <b>Audio Upload before Transcription:</b> Transcribing requires a valid physical audio file on disk linked to the database record. Calling <code>/transcribe</code> without an audio payload triggers HTTP 400.<br/>"
        "• <b>Transcription before Analysis:</b> The AI minutes generator (Qwen2.5) and sentiment analyzer (DistilBERT) require non-empty text input. Calling <code>/analyze</code> before <code>/transcribe</code> returns HTTP 400.<br/>"
        "• <b>Analysis before Summary Editing:</b> The summary editor allows organizers to refine AI-extracted points. Saving a summary (<code>PUT /summary</code>) creates a snapshot in <code>meeting_versions</code>.<br/>"
        "• <b>Finalization before PDF Export:</b> Exporting to PDF pulls directly from <code>meeting.summary</code>; generating the summary first ensures a rich, multi-section PDF document.",
        body_style
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # Section 2: Authentication & User Endpoints
    # -------------------------------------------------------------
    story.append(Paragraph("2. Authentication & User Profile Endpoints", h1_style))
    story.append(Paragraph(
        "Authentication uses JSON Web Tokens (JWT) signed with HMAC-SHA256. Tokens are transmitted in the HTTP <code>Authorization: Bearer &lt;token&gt;</code> header.",
        body_style
    ))

    # Helper function for endpoint cards
    def add_endpoint_card(method, path, badge_style, title, role, purpose, req_body, resp_sample):
        card_content = []
        header_text = f"<b>{title}</b> &nbsp;&nbsp;|&nbsp;&nbsp; <code>{path}</code>"
        card_content.append([
            Paragraph(f"<font size=9><b>{method}</b></font>", badge_style),
            Paragraph(header_text, tbl_cell_bold),
            Paragraph(f"<b>Role:</b> {role}", tbl_cell)
        ])
        t_hdr = Table(card_content, colWidths=[52, 340, 119])
        t_hdr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EEF2F6")),
            ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        
        detail_data = [
            [Paragraph("<b>Purpose</b>", tbl_cell_bold), Paragraph(purpose, tbl_cell)],
            [Paragraph("<b>Request</b>", tbl_cell_bold), Paragraph(req_body, code_style)],
            [Paragraph("<b>Response</b>", tbl_cell_bold), Paragraph(resp_sample, code_style)],
        ]
        t_detail = Table(detail_data, colWidths=[65, 446])
        t_detail.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#F1F5F9")),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        
        return KeepTogether([t_hdr, t_detail, Spacer(1, 6)])

    # POST /api/auth/register
    story.append(add_endpoint_card(
        "POST", "/api/auth/register", badge_post,
        "User Registration", "Public",
        "Registers a new Organizer or Participant user with hashed password and returns a JWT session token.",
        "JSON: {\"name\": \"Kalsoom Khan\", \"email\": \"kalsoom@fyp.test\", \"password\": \"Password@123\", \"role\": \"organizer\"}",
        "201 Created: {\"token\": \"eyJhbGciOiJIUzI1Ni...\", \"user\": {\"id\": \"usr_01\", \"name\": \"Kalsoom Khan\", \"email\": \"kalsoom@fyp.test\", \"role\": \"organizer\"}}"
    ))

    # POST /api/auth/login
    story.append(add_endpoint_card(
        "POST", "/api/auth/login", badge_post,
        "User Authentication", "Public",
        "Verifies credentials against stored password hash (Argon2/bcrypt) and returns a valid JWT session token.",
        "JSON: {\"email\": \"admin@smartmom.test\", \"password\": \"Admin@12345\"}",
        "200 OK: {\"token\": \"eyJhbGciOiJIUzI1Ni...\", \"user\": {\"id\": \"usr_admin\", \"name\": \"Admin\", \"email\": \"admin@smartmom.test\", \"role\": \"organizer\"}}"
    ))

    # GET /api/auth/me
    story.append(add_endpoint_card(
        "GET", "/api/auth/me", badge_get,
        "Current User Profile", "Authenticated User",
        "Validates the incoming Bearer token and returns identity and role metadata for the current session.",
        "Headers: Authorization: Bearer &lt;token&gt;",
        "200 OK: {\"id\": \"usr_admin\", \"name\": \"Admin\", \"email\": \"admin@smartmom.test\", \"role\": \"organizer\"}"
    ))

    # PUT /api/auth/me/role
    story.append(add_endpoint_card(
        "PUT", "/api/auth/me/role", badge_put,
        "Update Account Role", "Authenticated User",
        "Updates the user's default role between 'organizer' and 'participant'.",
        "JSON: {\"role\": \"participant\"}",
        "200 OK: {\"id\": \"usr_admin\", \"name\": \"Admin\", \"email\": \"admin@smartmom.test\", \"role\": \"participant\"}"
    ))

    # -------------------------------------------------------------
    # Section 3: Meeting Creation & Collaboration Endpoints
    # -------------------------------------------------------------
    story.append(Spacer(1, 4))
    story.append(Paragraph("3. Meeting Creation & Collaboration Endpoints", h1_style))

    # GET /api/meetings
    story.append(add_endpoint_card(
        "GET", "/api/meetings", badge_get,
        "List Accessible Meetings", "Authenticated User",
        "Returns all meetings owned by or shared with the authenticated user, ordered from newest to oldest.",
        "Headers: Authorization: Bearer &lt;token&gt;",
        "200 OK: [{\"id\": \"mtg_123\", \"title\": \"FYP Review\", \"status\": \"ready\", \"access_role\": \"organizer\", \"created_at\": \"2026-09-04T10:00:00Z\", ...}]"
    ))

    # POST /api/meetings
    story.append(add_endpoint_card(
        "POST", "/api/meetings", badge_post,
        "Create Meeting & Upload Audio", "Organizer / User",
        "Accepts multi-part audio file (WAV, MP3, M4A, OGG, WebM up to 200MB) and stores it safely under uploads/.",
        "multipart/form-data: audio=&lt;binary_file&gt; (required), title=\"Client Kickoff\" (optional)",
        "201 Created: {\"id\": \"mtg_abc123\", \"title\": \"Client Kickoff\", \"status\": \"uploaded\", \"access_role\": \"organizer\"}"
    ))

    # GET /api/meetings/{id}/participants
    story.append(add_endpoint_card(
        "GET", "/api/meetings/{id}/participants", badge_get,
        "List Meeting Members", "Organizer or Participant",
        "Retrieves the list of all users who have access to this meeting and their granted role.",
        "URL Param: id (string)<br/>Headers: Authorization: Bearer &lt;token&gt;",
        "200 OK: [{\"id\": \"u1\", \"name\": \"Organizer\", \"email\": \"admin@test.com\", \"access_role\": \"organizer\"}, {\"id\": \"u2\", \"name\": \"Participant\", \"email\": \"part@test.com\", \"access_role\": \"participant\"}]"
    ))

    # POST /api/meetings/{id}/participants
    story.append(add_endpoint_card(
        "POST", "/api/meetings/{id}/participants", badge_post,
        "Invite Participants", "Organizer Only",
        "Adds registered users to the meeting by email address so they can view summaries and submit feedback.",
        "JSON: {\"emails\": [\"part1@test.com\", \"part2@test.com\"]} (or comma-separated in \"email\")",
        "201 Created: {\"invited\": [{\"id\": \"u2\", \"email\": \"part1@test.com\", ...}], \"missing\": [\"part2@test.com\"]}"
    ))
    # -------------------------------------------------------------
    # Section 4: AI Transcription & Analysis Endpoints
    # -------------------------------------------------------------
    story.append(Spacer(1, 6))
    story.append(Paragraph("4. AI Transcription, Analysis & Versioning Endpoints", h1_style))

    # POST /api/meetings/{id}/transcribe
    story.append(add_endpoint_card(
        "POST", "/api/meetings/{id}/transcribe", badge_post,
        "Run Speech-to-Text Transcription", "Organizer Only",
        "Transcribes audio using local Whisper CPP (small.en-tdrz) with speaker-turn diarization into Speaker 1/2 segments.",
        "URL Param: id (string)<br/>Headers: Authorization: Bearer &lt;token&gt;",
        "200 OK: {\"text\": \"Speaker 1: Welcome...\\nSpeaker 2: I reviewed the tasks.\", \"segments\": [{\"speaker\": \"Speaker 1\", \"text\": \"Welcome...\"}], \"mode\": \"local-whisper\"}"
    ))

    # PUT /api/meetings/{id}/transcript
    story.append(add_endpoint_card(
        "PUT", "/api/meetings/{id}/transcript", badge_put,
        "Manual Transcript Correction", "Organizer Only",
        "Allows organizer to edit or replace transcript text before running downstream AI intelligence pipelines.",
        "JSON: {\"transcript\": \"Speaker 1: Let's start the project demo.\\nSpeaker 2: Documentation is completed.\"}",
        "204 No Content"
    ))

    # POST /api/meetings/{id}/analyze
    story.append(add_endpoint_card(
        "POST", "/api/meetings/{id}/analyze", badge_post,
        "Extract Minutes & Analyze Sentiment", "Organizer Only",
        "Executes dual AI pipelines: Quantized Qwen2.5 for structured minutes (agenda, decisions, actions) and DistilBERT for sentiment & engagement share.",
        "URL Param: id (string)<br/>Headers: Authorization: Bearer &lt;token&gt;",
        "200 OK: {\"summary\": {\"agenda\": [\"Review code\"], \"decisions\": [\"Merge branch\"], \"discussion\": [\"All tests passing\"], \"actions\": [{\"owner\": \"Kalsoom\", \"task\": \"Release candidate\", \"due\": \"Friday\"}]}, \"analysis\": {\"overall\": \"positive\", \"participants\": [{\"name\": \"Speaker 1\", \"sentiment\": \"Positive\", \"engagement\": 54}]}, \"mode\": \"local-qwen\"}"
    ))

    # PUT /api/meetings/{id}/summary
    story.append(add_endpoint_card(
        "PUT", "/api/meetings/{id}/summary", badge_put,
        "Save Refined Minutes & Version", "Organizer Only",
        "Saves human edits to agenda, decisions, discussion notes, and action items. Automatically appends a snapshot in meeting_versions for audit compliance.",
        "JSON: {\"summary\": {\"agenda\": [\"Project final signoff\"], \"decisions\": [\"Approved\"], \"discussion\": [...], \"actions\": [{\"owner\": \"Lead\", \"task\": \"Deploy to Docker\", \"due\": \"Monday\"}]}}",
        "200 OK: {\"summary\": {\"agenda\": [\"Project final signoff\"], ...}}"
    ))

    # -------------------------------------------------------------
    # Section 5: Export, Feedback & Cleanup Endpoints
    # -------------------------------------------------------------
    story.append(Spacer(1, 4))
    story.append(Paragraph("5. Export, Feedback & Cleanup Endpoints", h1_style))

    # GET /api/meetings/{id}/export.pdf
    story.append(add_endpoint_card(
        "GET", "/api/meetings/{id}/export.pdf", badge_get,
        "Export Formal PDF Minutes", "Organizer or Participant",
        "Dynamically generates and streams an A4 PDF document with clean headers, agenda, decisions, discussion notes, and assigned action item table.",
        "URL Param: id (string)<br/>Headers: Authorization: Bearer &lt;token&gt;",
        "200 OK (Binary Stream: application/pdf)<br/>Content-Disposition: attachment; filename=\"FYP-Review-minutes.pdf\""
    ))

    # POST /api/meetings/{id}/feedback
    story.append(add_endpoint_card(
        "POST", "/api/meetings/{id}/feedback", badge_post,
        "Submit Meeting Feedback", "Organizer or Participant",
        "Stores quality ratings (1 to 5 stars) and qualitative feedback comments from any authorized attendee.",
        "JSON: {\"rating\": 5, \"comment\": \"Accurate action items, loved the sentiment analysis breakdown!\"}",
        "201 Created: {\"ok\": true}"
    ))

    # DELETE /api/meetings/{id}
    story.append(add_endpoint_card(
        "DELETE", "/api/meetings/{id}", badge_delete,
        "Delete Meeting & Audio File", "Organizer Only",
        "Cascades deletion through database (members, versions, feedback) and permanently removes audio file from disk.",
        "URL Param: id (string)<br/>Headers: Authorization: Bearer &lt;token&gt;",
        "204 No Content"
    ))

    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 6: Permissions & RBAC Matrix
    # -------------------------------------------------------------
    story.append(Paragraph("6. Role-Based Access Control (RBAC) Matrix", h1_style))
    story.append(Paragraph(
        "The table below clarifies endpoint permissions based on user status and meeting role.",
        body_style
    ))

    rbac_data = [
        [
            Paragraph("<b>Endpoint</b>", tbl_header),
            Paragraph("<b>Method</b>", tbl_header),
            Paragraph("<b>Anonymous / Public</b>", tbl_header),
            Paragraph("<b>Participant</b>", tbl_header),
            Paragraph("<b>Meeting Organizer</b>", tbl_header),
        ],
        [Paragraph("/health", tbl_code), Paragraph("GET", tbl_cell), Paragraph("Allowed", tbl_cell), Paragraph("Allowed", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/auth/register", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Allowed", tbl_cell), Paragraph("N/A", tbl_cell), Paragraph("N/A", tbl_cell)],
        [Paragraph("/api/auth/login", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Allowed", tbl_cell), Paragraph("N/A", tbl_cell), Paragraph("N/A", tbl_cell)],
        [Paragraph("/api/auth/me", tbl_code), Paragraph("GET", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Allowed", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings", tbl_code), Paragraph("GET", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Allowed", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Allowed (Becomes Owner)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/participants", tbl_code), Paragraph("GET", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Allowed (If Member)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/participants", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Denied (404/403)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/transcribe", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Denied (404)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/transcript", tbl_code), Paragraph("PUT", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Denied (404)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/analyze", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Denied (404)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/summary", tbl_code), Paragraph("PUT", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Denied (404)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/export.pdf", tbl_code), Paragraph("GET", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Allowed (If Member)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}/feedback", tbl_code), Paragraph("POST", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Allowed (If Member)", tbl_cell), Paragraph("Allowed", tbl_cell)],
        [Paragraph("/api/meetings/{id}", tbl_code), Paragraph("DELETE", tbl_cell), Paragraph("Denied (401)", tbl_cell), Paragraph("Denied (404)", tbl_cell), Paragraph("Allowed", tbl_cell)],
    ]

    t_rbac = Table(rbac_data, colWidths=[150, 45, 95, 110, 111])
    t_rbac.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_rbac)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # Section 7: HTTP Status Codes & Troubleshooting
    # -------------------------------------------------------------
    story.append(Paragraph("7. Standard Error Codes & Troubleshooting", h1_style))
    story.append(Paragraph(
        "All error responses return a standardized JSON structure: <code>{\"error\": \"Descriptive message\"}</code>.",
        body_style
    ))

    error_data = [
        [Paragraph("<b>Status Code</b>", tbl_header), Paragraph("<b>Condition / Cause</b>", tbl_header), Paragraph("<b>Remediation / Resolution</b>", tbl_header)],
        [Paragraph("<b>400 Bad Request</b>", tbl_cell_bold), Paragraph("Unsupported audio MIME, missing email for invitation, or empty transcript submitted for analysis.", tbl_cell), Paragraph("Ensure audio is WAV/MP3/M4A/OGG/WebM; verify transcript is populated prior to analyze.", tbl_cell)],
        [Paragraph("<b>401 Unauthorized</b>", tbl_cell_bold), Paragraph("Missing Authorization header, invalid token, or expired session.", tbl_cell), Paragraph("Call /api/auth/login to get a fresh token and pass as 'Bearer &lt;token&gt;'.", tbl_cell)],
        [Paragraph("<b>404 Not Found</b>", tbl_cell_bold), Paragraph("Meeting does not exist, or current user lacks required access role.", tbl_cell), Paragraph("Verify meeting ID and ensure user has organizer role for modification requests.", tbl_cell)],
        [Paragraph("<b>409 Conflict</b>", tbl_cell_bold), Paragraph("Attempted registration with an email that is already registered.", tbl_cell), Paragraph("Use /api/auth/login or sign up with an alternative email address.", tbl_cell)],
        [Paragraph("<b>413 Payload Too Large</b>", tbl_cell_bold), Paragraph("Audio file exceeds MAX_UPLOAD_MB threshold (default 200 MB).", tbl_cell), Paragraph("Compress audio to mono 16kHz WAV or 64kbps MP3 prior to uploading.", tbl_cell)],
        [Paragraph("<b>503 Unavailable</b>", tbl_cell_bold), Paragraph("Local Whisper CLI / model files missing, or AI provider unconfigured.", tbl_cell), Paragraph("Run scripts/setup-local-whisper.ps1 or verify OPENAI_API_KEY if in cloud mode.", tbl_cell)],
    ]

    t_err = Table(error_data, colWidths=[100, 205, 206])
    t_err.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_err)

    # -------------------------------------------------------------
    # Page Canvas Numbering and Running Decorator
    # -------------------------------------------------------------
    def draw_decorations(canvas_obj, doc):
        canvas_obj.saveState()
        # Header (Pages 2+)
        if doc.page > 1:
            canvas_obj.setFont("Helvetica-Bold", 7.5)
            canvas_obj.setFillColor(C_MUTED)
            canvas_obj.drawString(MARGIN, PAGE_HEIGHT - 28, "SmartMOM Bot API — Reference & Integration Guide")
            canvas_obj.setFont("Helvetica", 7.5)
            canvas_obj.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 28, "FastAPI Endpoints & Lifecycle")
            canvas_obj.setStrokeColor(C_BORDER)
            canvas_obj.setLineWidth(0.5)
            canvas_obj.line(MARGIN, PAGE_HEIGHT - 32, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 32)

        # Footer (All pages)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(C_MUTED)
        canvas_obj.drawString(MARGIN, 22, "SmartMOM Bot © 2026 Final Year Project | Confidential & Internal")
        canvas_obj.drawRightString(PAGE_WIDTH - MARGIN, 22, f"Page {doc.page}")
        canvas_obj.setStrokeColor(C_BORDER)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(MARGIN, 30, PAGE_WIDTH - MARGIN, 30)
        canvas_obj.restoreState()

    import copy

    for out_path in output_paths:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN
        )
        # Create fresh copy of story for each target because doc.build mutates story in-place
        doc.build(copy.copy(story), onFirstPage=draw_decorations, onLaterPages=draw_decorations)
        print(f"Generated PDF successfully at: {out_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    root_dir = base_dir.parent
    
    targets = [
        base_dir / "docs" / "SmartMOM_API_Documentation.pdf",
        root_dir / "SmartMOM_API_Documentation.pdf"
    ]
    create_api_docs_pdf(targets)
