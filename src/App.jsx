import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Bot,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  Download,
  FileAudio,
  FileText,
  LayoutDashboard,
  LogOut,
  Mic,
  Plus,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Star,
  Trash2,
  Upload,
  UserRound,
  UsersRound,
  WandSparkles
} from 'lucide-react'
import './App.css'

const emptySummary = { agenda: [], decisions: [], discussion: [], actions: [] }
const tabs = ['Minutes', 'Transcript', 'Insights', 'People']

async function api(path, opts = {}) {
  const token = localStorage.getItem('smartmom_token')
  const response = await fetch(`/api${path}`, {
    ...opts,
    headers: {
      ...(opts.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  })
  const data = response.headers.get('content-type')?.includes('json') ? await response.json() : null
  if (!response.ok) throw Error(data?.error || 'Request failed.')
  return data
}

function initials(name = 'U') {
  return name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()
}

export default function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('smartmom_user') || 'null'))
  const [mode, setMode] = useState('login')
  const [authRole, setAuthRole] = useState('organizer')
  const [meetings, setMeetings] = useState([])
  const [selected, setSelected] = useState()
  const [activeTab, setActiveTab] = useState('Minutes')
  const [navView, setNavView] = useState('workspace')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [query, setQuery] = useState('')
  const [rating, setRating] = useState(0)
  const [feedback, setFeedback] = useState('')
  const [transcript, setTranscript] = useState('')
  const [summary, setSummary] = useState(emptySummary)
  const [recording, setRecording] = useState(false)
  const [participants, setParticipants] = useState([])
  const [inviteEmail, setInviteEmail] = useState('')
  const fileInput = useRef()
  const recorder = useRef()
  const chunks = useRef([])

  const current = meetings.find((meeting) => meeting.id === selected)
  const isOrganizer = current?.access_role === 'organizer'

  async function loadMeetings(selectFirst = false) {
    try {
      const data = await api('/meetings')
      setMeetings(data)
      if ((selectFirst || !selected) && data[0]) setSelected(data[0].id)
      if (selected && !data.some((meeting) => meeting.id === selected)) setSelected(data[0]?.id)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function loadParticipants(meetingId) {
    if (!meetingId) return
    try {
      setParticipants(await api(`/meetings/${meetingId}/participants`))
    } catch (error) {
      setNotice(error.message)
    }
  }

  useEffect(() => {
    if (user) loadMeetings(true)
  }, [user])

  useEffect(() => {
    if (!current) return
    setTranscript(current.transcript || '')
    setSummary(current.summary || emptySummary)
    loadParticipants(current.id)
  }, [current?.id])

  async function authenticate(event) {
    event.preventDefault()
    const payload = Object.fromEntries(new FormData(event.currentTarget))
    if (mode === 'register') payload.role = authRole
    try {
      const data = await api(`/auth/${mode}`, { method: 'POST', body: JSON.stringify(payload) })
      localStorage.setItem('smartmom_token', data.token)
      localStorage.setItem('smartmom_user', JSON.stringify(data.user))
      setUser(data.user)
      setNotice('')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function uploadAudio(file) {
    if (!file) return
    if (file.size > 200 * 1024 * 1024) return setNotice('Audio files must be below 200 MB.')
    setBusy(true)
    try {
      const form = new FormData()
      form.append('audio', file)
      form.append('title', file.name.replace(/\.[^.]+$/, ''))
      const meeting = await api('/meetings', { method: 'POST', body: form })
      await loadMeetings()
      setSelected(meeting.id)
      setNotice('Meeting audio uploaded. Review, transcribe, and generate minutes when ready.')
    } catch (error) {
      setNotice(error.message)
    } finally {
      setBusy(false)
    }
  }

  function startNewMeeting() {
    if (user.role !== 'organizer') {
      setNotice('Your current account role is Participant. Use “Switch to Organizer” in the profile area, then try again.')
      return
    }
    setNavView('workspace')
    fileInput.current?.click()
  }

  async function switchToOrganizer() {
    try {
      const updatedUser = await api('/auth/me/role', { method: 'PUT', body: JSON.stringify({ role: 'organizer' }) })
      localStorage.setItem('smartmom_user', JSON.stringify(updatedUser))
      setUser(updatedUser)
      setNotice('You are now an Organizer. You can create a new meeting.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function recordAudio() {
    if (recording) {
      recorder.current.stop()
      setRecording(false)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunks.current = []
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorder.ondataavailable = (event) => chunks.current.push(event.data)
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        uploadAudio(new File(chunks.current, `Meeting-${Date.now()}.webm`, { type: 'audio/webm' }))
      }
      mediaRecorder.start()
      recorder.current = mediaRecorder
      setRecording(true)
      setNotice('Recording started. Make sure every participant has consented.')
    } catch {
      setNotice('Microphone permission was not granted.')
    }
  }

  async function saveTranscript() {
    if (!current || !isOrganizer) return
    await api(`/meetings/${selected}/transcript`, { method: 'PUT', body: JSON.stringify({ transcript }) })
    await loadMeetings()
  }

  async function transcribeMeeting() {
    setBusy(true)
    try {
      const data = await api(`/meetings/${selected}/transcribe`, { method: 'POST' })
      setTranscript(data.text)
      await loadMeetings()
      setNotice('Transcription complete. Review speaker labels before AI analysis.')
    } catch (error) {
      setNotice(error.message)
    } finally {
      setBusy(false)
    }
  }

  async function analyzeMeeting() {
    setBusy(true)
    try {
      await saveTranscript()
      const data = await api(`/meetings/${selected}/analyze`, { method: 'POST' })
      setSummary(data.summary)
      await loadMeetings()
      setActiveTab('Minutes')
      setNotice('AI minutes, decisions, action items, sentiment, and engagement are ready for review.')
    } catch (error) {
      setNotice(error.message)
    } finally {
      setBusy(false)
    }
  }

  async function saveSummary() {
    if (!isOrganizer) return
    try {
      await api(`/meetings/${selected}/summary`, { method: 'PUT', body: JSON.stringify({ summary }) })
      await loadMeetings()
      setNotice('Minutes saved with version history.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function deleteMeeting() {
    if (!confirm('Permanently delete this meeting, audio, minutes, versions, and feedback?')) return
    try {
      await api(`/meetings/${selected}`, { method: 'DELETE' })
      setSelected(undefined)
      await loadMeetings(true)
      setNotice('Meeting deleted.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function exportPdf() {
    try {
      const response = await fetch(`/api/meetings/${selected}/export.pdf`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('smartmom_token')}` }
      })
      if (!response.ok) throw Error('PDF export failed.')
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = `${current.title}-minutes.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function inviteParticipant(event) {
    event.preventDefault()
    try {
      const data = await api(`/meetings/${selected}/participants`, { method: 'POST', body: JSON.stringify({ email: inviteEmail }) })
      await loadParticipants(selected)
      setInviteEmail('')
      setNotice(data.missing.length ? `Added ${data.invited.length}. Not registered: ${data.missing.join(', ')}` : 'Participant access updated.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function sendFeedback() {
    try {
      await api(`/meetings/${selected}/feedback`, { method: 'POST', body: JSON.stringify({ rating, comment: feedback }) })
      setRating(0)
      setFeedback('')
      setNotice('Feedback saved for this meeting.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  const filteredMeetings = useMemo(() => {
    return meetings.filter((meeting) => `${meeting.title} ${meeting.status} ${meeting.transcript || ''}`.toLowerCase().includes(query.toLowerCase()))
  }, [meetings, query])

  if (!user) {
    return <AuthScreen mode={mode} setMode={setMode} authRole={authRole} setAuthRole={setAuthRole} authenticate={authenticate} notice={notice} />
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span><Bot size={20} /></span>
          <div>
            <strong>SmartMOM</strong>
            <small>AI Meeting Minutes</small>
          </div>
        </div>
        <button className="primary-action" onClick={startNewMeeting}>
          <Plus size={18} /> New meeting
        </button>
        <input ref={fileInput} hidden type="file" accept="audio/mpeg,audio/wav,audio/mp4,audio/ogg,audio/webm" onChange={(event) => uploadAudio(event.target.files[0])} />
        <nav className="main-nav">
          <button className={navView === 'workspace' ? 'active' : ''} onClick={() => setNavView('workspace')}><LayoutDashboard size={17} /> Workspace</button>
          <button className={navView === 'archive' ? 'active' : ''} onClick={() => setNavView('archive')}><FileText size={17} /> Minutes archive</button>
          <button className={navView === 'review' ? 'active' : ''} onClick={() => setNavView('review')}><ShieldCheck size={17} /> Review queue</button>
        </nav>
        <div className="meeting-list-head">
          <span>Meetings</span>
          <strong>{meetings.length}</strong>
        </div>
        <div className="meeting-list">
          {meetings.map((meeting) => (
            <button className={`meeting-row ${meeting.id === selected ? 'selected' : ''}`} onClick={() => { setSelected(meeting.id); setNavView('workspace') }} key={meeting.id}>
              <span>{meeting.title}</span>
              <small>{meeting.access_role} / {meeting.status}</small>
            </button>
          ))}
        </div>
        <div className="profile-card">
          <span className="avatar">{initials(user.name)}</span>
          <div>
            <strong>{user.name}</strong>
            <small>{user.role} / {user.email}</small>
          </div>
          {user.role !== 'organizer' && <button className="role-upgrade" title="Switch to Organizer" onClick={switchToOrganizer}><ShieldCheck size={15} /> Organizer</button>}
          <button title="Sign out" onClick={() => { localStorage.clear(); setUser(null) }}><LogOut size={17} /></button>
        </div>
      </aside>

      <main className="workspace">
        {notice && <div className="notice"><span>{notice}</span><button onClick={() => setNotice('')}>Dismiss</button></div>}
        {navView === 'archive' ? (
          <MeetingDirectory title="Minutes archive" subtitle="Browse every meeting record you can access." meetings={meetings} onOpen={(meeting) => { setSelected(meeting.id); setNavView('workspace') }} />
        ) : navView === 'review' ? (
          <MeetingDirectory title="Review queue" subtitle="Meetings that still need transcript, AI review, or final approval." meetings={meetings.filter((meeting) => meeting.status !== 'saved')} onOpen={(meeting) => { setSelected(meeting.id); setNavView('workspace') }} emptyMessage="Everything is reviewed. Your queue is clear." />
        ) : !current ? (
          <EmptyState user={user} upload={startNewMeeting} />
        ) : (
          <>
            <WorkspaceHeader current={current} isOrganizer={isOrganizer} saveSummary={saveSummary} exportPdf={exportPdf} />
            <WorkflowBar current={current} />
            <div className="work-grid">
              <section className="work-panel">
                <Toolbar
                  user={user}
                  isOrganizer={isOrganizer}
                  recording={recording}
                  busy={busy}
                  recordAudio={recordAudio}
                  transcribeMeeting={transcribeMeeting}
                  analyzeMeeting={analyzeMeeting}
                  upload={() => fileInput.current?.click()}
                />
                <div className="tabs">
                  {tabs.map((tab) => <button className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>)}
                </div>
                {activeTab === 'Minutes' && <MinutesView summary={summary} setSummary={setSummary} isOrganizer={isOrganizer} saveSummary={saveSummary} analyzeMeeting={analyzeMeeting} deleteMeeting={deleteMeeting} busy={busy} />}
                {activeTab === 'Transcript' && <TranscriptView transcript={transcript} setTranscript={setTranscript} saveTranscript={saveTranscript} analyzeMeeting={analyzeMeeting} isOrganizer={isOrganizer} />}
                {activeTab === 'Insights' && <InsightsView analysis={current.analysis} />}
                {activeTab === 'People' && <PeopleView participants={participants} isOrganizer={isOrganizer} inviteEmail={inviteEmail} setInviteEmail={setInviteEmail} inviteParticipant={inviteParticipant} />}
              </section>
              <aside className="detail-rail">
                <SearchCard query={query} setQuery={setQuery} results={filteredMeetings} setSelected={setSelected} />
                <FeedbackCard rating={rating} setRating={setRating} feedback={feedback} setFeedback={setFeedback} sendFeedback={sendFeedback} />
                <MeetingHealth current={current} summary={summary} participants={participants} />
              </aside>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

function AuthScreen({ mode, setMode, authRole, setAuthRole, authenticate, notice }) {
  return (
    <div className="auth-screen">
      <section className="auth-visual">
        <div className="brand-lockup large">
          <span><Bot size={26} /></span>
          <div>
            <strong>SmartMOM</strong>
            <small>Real-time meeting intelligence</small>
          </div>
        </div>
        <div className="auth-metrics">
          <div><strong>UC1-UC10</strong><span>implemented workflow</span></div>
          <div><strong>2 roles</strong><span>Organizer and Participant</span></div>
          <div><strong>PDF</strong><span>exportable minutes</span></div>
        </div>
      </section>
      <form className="auth-form" onSubmit={authenticate}>
        <span className="eyebrow">{mode === 'login' ? 'Secure sign in' : 'Create workspace account'}</span>
        <h1>{mode === 'login' ? 'Welcome back' : 'Register for SmartMOM'}</h1>
        {mode === 'register' && (
          <>
            <div className="role-switch">
              <button type="button" className={authRole === 'organizer' ? 'selected' : ''} onClick={() => setAuthRole('organizer')}>
                <ShieldCheck size={19} /><span>Organizer</span><small>Create, process, edit, export</small>
              </button>
              <button type="button" className={authRole === 'participant' ? 'selected' : ''} onClick={() => setAuthRole('participant')}>
                <UserRound size={19} /><span>Participant</span><small>Review minutes and feedback</small>
              </button>
            </div>
            <input name="name" required placeholder="Full name" />
          </>
        )}
        <input name="email" type="email" required placeholder="Work email" />
        <input name="password" type="password" minLength="10" required placeholder="Password (10+ characters)" />
        <button className="dark-button">{mode === 'login' ? 'Sign in' : 'Create account'}</button>
        <button className="text-button" type="button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Need an account? Register' : 'Already registered? Sign in'}
        </button>
        {notice && <p className="form-error">{notice}</p>}
      </form>
    </div>
  )
}

function EmptyState({ user, upload }) {
  return (
    <section className="empty-state">
      <FileAudio size={44} />
      <h1>{user.role === 'organizer' ? 'Upload the first meeting audio' : 'No shared meetings yet'}</h1>
      <p>{user.role === 'organizer' ? 'Create a real meeting workspace from an audio file or live recording.' : 'Ask an Organizer to invite this registered email to a meeting.'}</p>
      {user.role === 'organizer' && <button onClick={upload}><Upload size={17} /> Upload audio</button>}
    </section>
  )
}

function MeetingDirectory({ title, subtitle, meetings, onOpen, emptyMessage = 'No meeting records are available yet.' }) {
  return (
    <section className="meeting-directory">
      <span className="eyebrow">SmartMOM workspace</span>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      {meetings.length ? <div className="directory-list">{meetings.map((meeting) => (
        <button key={meeting.id} onClick={() => onOpen(meeting)}>
          <span className="directory-icon"><FileText size={19} /></span>
          <span><strong>{meeting.title}</strong><small>{new Date(meeting.created_at).toLocaleString()}</small></span>
          <em>{meeting.status}</em><ChevronRight size={18} />
        </button>
      ))}</div> : <div className="directory-empty"><FileText size={30} /><strong>{emptyMessage}</strong></div>}
    </section>
  )
}

function WorkspaceHeader({ current, isOrganizer, saveSummary, exportPdf }) {
  return (
    <header className="workspace-header">
      <div>
        <span className="eyebrow">Meeting workspace</span>
        <h1>{current.title}</h1>
        <p><CalendarClock size={15} /> {new Date(current.created_at).toLocaleString()} <span>{current.access_role}</span></p>
      </div>
      <div className="header-actions">
        {isOrganizer && <button onClick={saveSummary}><Save size={17} /> Save</button>}
        <button className="dark-button compact" onClick={exportPdf}><Download size={17} /> Export PDF</button>
      </div>
    </header>
  )
}

function WorkflowBar({ current }) {
  const steps = [
    ['Audio', ['uploaded', 'transcribing', 'transcribed', 'ready', 'saved', 'failed'].includes(current.status)],
    ['Transcript', ['transcribed', 'ready', 'saved'].includes(current.status)],
    ['AI review', ['ready', 'saved'].includes(current.status)],
    ['Minutes', current.status === 'saved']
  ]
  return <div className="workflow-bar">{steps.map(([label, done]) => <div className={done ? 'done' : ''} key={label}><CheckCircle2 size={16} /> {label}</div>)}</div>
}

function Toolbar({ user, isOrganizer, recording, busy, recordAudio, transcribeMeeting, analyzeMeeting, upload }) {
  if (!isOrganizer) return <div className="readonly-banner"><UsersRound size={18} /> Participant review mode is active for this meeting.</div>
  return (
    <div className="tool-strip">
      <button onClick={upload} disabled={user.role !== 'organizer'}><Upload size={17} /> Upload</button>
      <button onClick={recordAudio}>{recording ? <Square size={17} /> : <Mic size={17} />} {recording ? 'Stop' : 'Record'}</button>
      <button onClick={transcribeMeeting} disabled={busy}><FileText size={17} /> {busy ? 'Working' : 'Transcribe'}</button>
      <button onClick={analyzeMeeting} disabled={busy}><WandSparkles size={17} /> Analyze</button>
    </div>
  )
}

function MinutesView({ summary, setSummary, isOrganizer, saveSummary, analyzeMeeting, deleteMeeting, busy }) {
  return (
    <div className="minutes-view">
      <div className="section-head">
        <div><span className="eyebrow">Reviewed minutes</span><h2>Structured meeting record</h2></div>
        {isOrganizer && <button onClick={analyzeMeeting} disabled={busy}><Sparkles size={17} /> {busy ? 'Analyzing' : 'Generate with AI'}</button>}
      </div>
      <EditableList title="Agenda" items={summary.agenda} onChange={(items) => setSummary({ ...summary, agenda: items })} readonly={!isOrganizer} />
      <EditableList title="Key decisions" items={summary.decisions} onChange={(items) => setSummary({ ...summary, decisions: items })} readonly={!isOrganizer} />
      <EditableList title="Discussion points" items={summary.discussion} onChange={(items) => setSummary({ ...summary, discussion: items })} readonly={!isOrganizer} />
      <ActionItems actions={summary.actions} setActions={(actions) => setSummary({ ...summary, actions })} readonly={!isOrganizer} />
      {isOrganizer && <div className="footer-actions"><button onClick={saveSummary}><Save size={17} /> Save changes</button><button className="danger" onClick={deleteMeeting}><Trash2 size={17} /> Delete</button></div>}
    </div>
  )
}

function EditableList({ title, items = [], onChange, readonly }) {
  const list = items.length ? items : ['']
  return (
    <section className="content-section">
      <h3>{title}</h3>
      {list.map((item, index) => (
        <label className="editable-line" key={`${title}-${index}`}>
          <ChevronRight size={15} />
          <input value={item} readOnly={readonly} placeholder={`Add ${title.toLowerCase()}`} onChange={(event) => {
            const next = [...list]
            next[index] = event.target.value
            onChange(next)
          }} />
        </label>
      ))}
      {!readonly && <button className="add-line" onClick={() => onChange([...items, ''])}><Plus size={15} /> Add line</button>}
    </section>
  )
}

function ActionItems({ actions = [], setActions, readonly }) {
  const list = actions.length ? actions : [{ owner: '', task: '', due: '' }]
  return (
    <section className="content-section">
      <h3>Action items</h3>
      <div className="action-table">
        <span>Owner</span><span>Task</span><span>Due</span>
        {list.map((action, index) => (
          <div className="action-row" key={index}>
            <input readOnly={readonly} value={action.owner || ''} placeholder="Owner" onChange={(event) => {
              const next = [...list]
              next[index] = { ...action, owner: event.target.value }
              setActions(next)
            }} />
            <input readOnly={readonly} value={action.task || ''} placeholder="Task" onChange={(event) => {
              const next = [...list]
              next[index] = { ...action, task: event.target.value }
              setActions(next)
            }} />
            <input readOnly={readonly} value={action.due || ''} placeholder="Due date" onChange={(event) => {
              const next = [...list]
              next[index] = { ...action, due: event.target.value }
              setActions(next)
            }} />
          </div>
        ))}
      </div>
      {!readonly && <button className="add-line" onClick={() => setActions([...actions, { owner: '', task: '', due: '' }])}><Plus size={15} /> Add action</button>}
    </section>
  )
}

function TranscriptView({ transcript, setTranscript, saveTranscript, analyzeMeeting, isOrganizer }) {
  return (
    <div className="transcript-view">
      <div className="section-head">
        <div><span className="eyebrow">Speaker transcript</span><h2>Review conversation text</h2></div>
        {isOrganizer && <button onClick={analyzeMeeting}><WandSparkles size={17} /> Analyze transcript</button>}
      </div>
      <textarea value={transcript} readOnly={!isOrganizer} onChange={(event) => setTranscript(event.target.value)} onBlur={() => saveTranscript().catch(() => {})} placeholder="Transcript appears here after audio transcription." />
    </div>
  )
}

function InsightsView({ analysis = {} }) {
  const participants = analysis.participants || []
  return (
    <div className="insights-view">
      <div className="section-head"><div><span className="eyebrow">Sentiment and engagement</span><h2>{analysis.overall || 'Not analyzed yet'}</h2></div></div>
      <div className="people-grid">
        {participants.length ? participants.map((person) => (
          <div className="person-card" key={person.name}>
            <span className="avatar">{initials(person.name)}</span>
            <strong>{person.name}</strong>
            <small>{person.sentiment || 'Neutral'} sentiment</small>
            <i><u style={{ width: `${Math.min(100, Math.max(0, person.engagement || 0))}%` }} /></i>
            <small>{person.engagement || 0}% engagement</small>
          </div>
        )) : <p className="muted">Run AI analysis after transcription to view per-participant sentiment and engagement.</p>}
      </div>
    </div>
  )
}

function PeopleView({ participants, isOrganizer, inviteEmail, setInviteEmail, inviteParticipant }) {
  return (
    <div className="people-view">
      <div className="section-head"><div><span className="eyebrow">Registered users</span><h2>Meeting access</h2></div></div>
      {isOrganizer && (
        <form className="invite-form" onSubmit={inviteParticipant}>
          <input value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="participant@company.com" />
          <button><UsersRound size={17} /> Invite</button>
        </form>
      )}
      <div className="member-list">
        {participants.map((member) => <div className="member-row" key={member.id}><span className="avatar">{initials(member.name)}</span><div><strong>{member.name}</strong><small>{member.email}</small></div><em>{member.access_role}</em></div>)}
      </div>
    </div>
  )
}

function SearchCard({ query, setQuery, results, setSelected }) {
  return (
    <section className="rail-card">
      <span className="eyebrow">Archive search</span>
      <label className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search meetings" /></label>
      {query && results.slice(0, 5).map((meeting) => <button className="search-result" onClick={() => setSelected(meeting.id)} key={meeting.id}>{meeting.title}</button>)}
    </section>
  )
}

function FeedbackCard({ rating, setRating, feedback, setFeedback, sendFeedback }) {
  return (
    <section className="rail-card">
      <span className="eyebrow">Feedback</span>
      <h3>Summary quality</h3>
      <div className="stars">{[1, 2, 3, 4, 5].map((value) => <button className={value <= rating ? 'lit' : ''} onClick={() => setRating(value)} key={value}><Star size={18} fill="currentColor" /></button>)}</div>
      <textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Accuracy or clarity notes" />
      <button className="wide-button" onClick={sendFeedback}>Submit feedback</button>
    </section>
  )
}

function MeetingHealth({ current, summary, participants }) {
  const actionCount = summary.actions?.filter((action) => action.task).length || 0
  return (
    <section className="rail-card health">
      <span className="eyebrow">Meeting health</span>
      <div><strong>{current.status}</strong><small>Current status</small></div>
      <div><strong>{actionCount}</strong><small>Action items</small></div>
      <div><strong>{participants.length}</strong><small>Registered users</small></div>
    </section>
  )
}
