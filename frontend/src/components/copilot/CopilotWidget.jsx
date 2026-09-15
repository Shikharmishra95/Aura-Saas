import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  ArrowUp, 
  Sparkles, 
  Bot, 
  RefreshCw, 
  CheckCircle2, 
  Stethoscope, 
  Calendar, 
  Clock, 
  DollarSign, 
  Activity, 
  Users, 
  ChevronRight, 
  ShieldCheck, 
  FileText, 
  Palmtree,
  UserCheck,
  Building2,
  TrendingUp,
  AlertCircle
} from 'lucide-react';

export default function CopilotWidget({
  token,
  userRole,
  username,
  activeHospital,
  activeTab,
  selectedDate,
  t
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  // Dynamic configuration for Role-Specific Hero Cards & Suggestions
  const getRoleConfig = () => {
    const role = (userRole || 'STAFF').toUpperCase();
    const hospName = activeHospital?.name || 'AURA Hospital';
    const cleanUsername = username ? (username.startsWith('Dr.') ? username : `Dr. ${username}`) : 'Doctor';

    if (role === 'DOCTOR') {
      return {
        welcomeTitle: `How can I help you today, ${cleanUsername}?`,
        welcomeSubtitle: `I'm AURA Copilot for ${hospName}. Check your live queue, consultations, OPD earnings, or shifts in seconds.`,
        primaryCard: {
          icon: <Users size={20} color="#C4B5FD" />,
          title: "Show My Live Waiting Room Queue",
          subtitle: "Live OPD tokens, waiting list & patient complaints",
          query: "How many patients are waiting in my queue?"
        },
        gridCards: [
          {
            icon: <Clock size={16} color="#A78BFA" />,
            title: "My Shift Timings",
            subtitle: "Check tomorrow OPD hours",
            query: "What are my shift timings for tomorrow?"
          },
          {
            icon: <Stethoscope size={16} color="#34D399" />,
            title: "Consulted Patients",
            subtitle: "Today's completed visits",
            query: "Today's total consulted patients"
          },
          {
            icon: <DollarSign size={16} color="#FBBF24" />,
            title: "OPD Earnings Today",
            subtitle: "Revenue & collection count",
            query: "What are my OPD earnings today?"
          },
          {
            icon: <Palmtree size={16} color="#F472B6" />,
            title: "Apply Leave",
            subtitle: "Request upcoming day off",
            query: "Apply for leave next Monday"
          }
        ],
        suggestions: [
          "How many patients are waiting in my queue?",
          "What is the next patient's chief complaint?",
          "What are my shift timings for tomorrow?",
          "Check my approved leave status",
          "Today's total consulted patients",
          "What are my OPD earnings today?"
        ]
      };
    }

    if (role === 'ADMIN') {
      return {
        welcomeTitle: `Welcome, Hospital Admin`,
        welcomeSubtitle: `AURA Copilot analytics for ${hospName}. Monitor doctor rosters, OPD collection, and appointment trends.`,
        primaryCard: {
          icon: <TrendingUp size={20} color="#C4B5FD" />,
          title: "Monthly OPD Revenue Overview",
          subtitle: "Total collections, dues, and payment metrics",
          query: "What is our total OPD revenue for this month?"
        },
        gridCards: [
          {
            icon: <Users size={16} color="#38BDF8" />,
            title: "Doctor Performance",
            subtitle: "Appointment loads per doctor",
            query: "Show doctor-wise booking performance"
          },
          {
            icon: <Building2 size={16} color="#A78BFA" />,
            title: "Departments & Doctors",
            subtitle: "Directory and active rosters",
            query: "Show active departments and doctors directory"
          },
          {
            icon: <AlertCircle size={16} color="#FB7185" />,
            title: "Cancelled Appointments",
            subtitle: "Today's cancellations & reasons",
            query: "How many appointments were cancelled today?"
          },
          {
            icon: <DollarSign size={16} color="#FBBF24" />,
            title: "Pending Dues",
            subtitle: "Uncollected balance summary",
            query: "Pending collection dues summary"
          }
        ],
        suggestions: [
          "What is our total OPD revenue for this month?",
          "Show doctor-wise booking performance",
          "Show active departments and doctors directory",
          "How many appointments were cancelled today?",
          "Pending collection dues summary"
        ]
      };
    }

    if (role === 'SUPER_ADMIN') {
      return {
        welcomeTitle: `AURA Platform Copilot`,
        welcomeSubtitle: `Global multi-tenant overview across all hospital subscriptions and AI voice telemetry.`,
        primaryCard: {
          icon: <Building2 size={20} color="#C4B5FD" />,
          title: "Active Hospitals & Subscriptions",
          subtitle: "Global tenant health and active nodes",
          query: "How many hospitals are active on AURA platform?"
        },
        gridCards: [
          {
            icon: <Clock size={16} color="#FBBF24" />,
            title: "Expiring Plans",
            subtitle: "Subscriptions renewing in 30 days",
            query: "Which subscriptions are expiring in next 30 days?"
          },
          {
            icon: <Activity size={16} color="#34D399" />,
            title: "Voice AI Traffic",
            subtitle: "Total calls handled today",
            query: "Total AI voice calls processed today"
          },
          {
            icon: <TrendingUp size={16} color="#A78BFA" />,
            title: "Platform Revenue",
            subtitle: "Global monthly run-rate",
            query: "Platform monthly revenue overview"
          },
          {
            icon: <ShieldCheck size={16} color="#38BDF8" />,
            title: "Tenant Roster",
            subtitle: "List of all hospital tenants",
            query: "Show all active hospital tenants"
          }
        ],
        suggestions: [
          "How many hospitals are active on AURA platform?",
          "Which subscriptions are expiring in next 30 days?",
          "Total AI voice calls processed today",
          "Platform monthly revenue overview"
        ]
      };
    }

    // Receptionist / Front Desk
    return {
      welcomeTitle: `Front Desk Copilot`,
      welcomeSubtitle: `Instant patient lookups, doctor roster schedules, OPD tokens, and appointment bookings.`,
      primaryCard: {
        icon: <Activity size={20} color="#C4B5FD" />,
        title: "Today's OPD Queue Summary",
        subtitle: "Check total waiting, booked & consulted patients",
        query: "Today's OPD Queue Summary"
      },
      gridCards: [
        {
          icon: <UserCheck size={16} color="#34D399" />,
          title: "Doctors on Duty",
          subtitle: "Who is available today?",
          query: "Which doctors are on duty today?"
        },
        {
          icon: <Calendar size={16} color="#38BDF8" />,
          title: "Tomorrow's Doctors",
          subtitle: "Check upcoming schedules",
          query: "Which doctors are available tomorrow?"
        },
        {
          icon: <DollarSign size={16} color="#FBBF24" />,
          title: "Fees & Shift Timings",
          subtitle: "Department fee breakdown",
          query: "Show all doctor shift timings and OPD fees"
        },
        {
          icon: <Palmtree size={16} color="#F472B6" />,
          title: "Doctor Leave Status",
          subtitle: "Check approved doctor leaves",
          query: "Check if any doctor is on approved leave"
        }
      ],
      suggestions: [
        "Today's OPD Queue Summary",
        "Which doctors are on duty today?",
        "Which doctors are available tomorrow?",
        "Show all doctor shift timings and OPD fees",
        "Check if any doctor is on approved leave",
        "List of missed and cancelled patients today"
      ]
    };
  };

  const roleConfig = getRoleConfig();

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const hospName = activeHospital?.name || 'AURA SaaS';
      const roleDisplayName = (userRole || 'STAFF').replace('_', ' ');
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `Hello ${username || 'there'}! I am your **AURA AI Copilot** for **${hospName}** (${roleDisplayName}).\n\nI can instantly check doctor shift schedules, live appointment queues, open booking slots, patient records, and revenue analytics. Feel free to ask anything!`
        }
      ]);
    }
  }, [isOpen, activeHospital, activeTab, username, userRole]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading) return;

    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: text
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInputMessage('');
    setLoading(true);

    try {
      const res = await fetch('/api/v1/copilot/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
          active_tab: activeTab || 'overview',
          selected_date: selectedDate || ''
        })
      });

      if (!res.ok) {
        throw new Error("Failed to get response from AI Copilot.");
      }

      const data = await res.json();
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.reply,
          toolUsed: data.tool_used
        }
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: "Sorry, I encountered an issue connecting to the AI server. Please check your connection and try again."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Markdown parser with Hostinger-style bright highlights
  const renderFormattedContent = (content) => {
    if (!content) return '';
    const lines = content.split('\n');
    return lines.map((line, lIdx) => {
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const formattedParts = parts.map((p, pIdx) => {
        if (p.startsWith('**') && p.endsWith('**')) {
          return (
            <strong key={pIdx} style={{ color: '#DDD6FE', fontWeight: 700 }}>
              {p.slice(2, -2)}
            </strong>
          );
        }
        return p;
      });

      return (
        <div key={lIdx} style={{ minHeight: line.trim() === '' ? '6px' : 'auto', marginBottom: '3px' }}>
          {formattedParts}
        </div>
      );
    });
  };

  if (!token) return null;

  return (
    <>
      {/* Floating Action Button (Hostinger Glowing Obsidian Badge) */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: 'linear-gradient(135deg, #18112C 0%, #0F0A1E 100%)',
            color: '#FFFFFF',
            border: '1.5px solid rgba(139, 92, 246, 0.45)',
            borderRadius: '50px',
            padding: '10px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: '0 8px 30px rgba(124, 58, 237, 0.35), 0 0 20px rgba(139, 92, 246, 0.2)',
            cursor: 'pointer',
            zIndex: 9998,
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
            fontWeight: 700,
            fontSize: '13.5px',
            backdropFilter: 'blur(12px)'
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-3px) scale(1.03)';
            e.currentTarget.style.boxShadow = '0 12px 35px rgba(124, 58, 237, 0.55), 0 0 25px rgba(139, 92, 246, 0.35)';
            e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.7)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0) scale(1)';
            e.currentTarget.style.boxShadow = '0 8px 30px rgba(124, 58, 237, 0.35), 0 0 20px rgba(139, 92, 246, 0.2)';
            e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.45)';
          }}
        >
          <div style={{
            background: 'linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)',
            width: '26px',
            height: '26px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 10px rgba(139, 92, 246, 0.6)'
          }}>
            <Sparkles size={14} color="#FFFFFF" />
          </div>
          <span style={{ letterSpacing: '0.2px' }}>AURA Copilot</span>
          <span style={{
            display: 'inline-block',
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            background: '#22C55E',
            boxShadow: '0 0 8px #22C55E'
          }}></span>
        </button>
      )}

      {/* Expandable Chat Window (Hostinger Agent Obsidian Glassmorphic Design) */}
      {isOpen && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          width: '420px',
          height: '630px',
          maxHeight: 'calc(100vh - 40px)',
          background: 'linear-gradient(180deg, #090714 0%, #0E0A22 45%, #140E2F 100%)',
          borderRadius: '24px',
          boxShadow: '0 25px 60px -10px rgba(0, 0, 0, 0.8), 0 0 35px rgba(124, 58, 237, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
          border: '1px solid rgba(139, 92, 246, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 9999,
          overflow: 'hidden',
          backdropFilter: 'blur(20px)',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          animation: 'fadeSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)'
        }}>
          {/* Header */}
          <div style={{
            padding: '14px 18px',
            background: 'rgba(15, 10, 33, 0.75)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backdropFilter: 'blur(10px)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
              <div style={{
                background: 'linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)',
                width: '36px',
                height: '36px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 14px rgba(124, 58, 237, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.4)'
              }}>
                <Sparkles size={18} color="#FFFFFF" />
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: '15px', color: '#FFFFFF', letterSpacing: '-0.2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>AURA Copilot</span>
                  <span style={{
                    fontSize: '9.5px',
                    fontWeight: 700,
                    color: '#A78BFA',
                    background: 'rgba(139, 92, 246, 0.18)',
                    padding: '1px 6px',
                    borderRadius: '6px',
                    border: '1px solid rgba(139, 92, 246, 0.3)'
                  }}>AI</span>
                </div>
                <div style={{ fontSize: '11px', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '5px', marginTop: '1px' }}>
                  <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#22C55E', boxShadow: '0 0 6px #22C55E' }}></span>
                  <span>Online</span> • <span style={{ color: '#CBD5E1', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{activeHospital?.name || 'Hospital'}</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={() => {
                  setMessages([]);
                  setConversationId(null);
                }}
                title="Reset chat"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  color: '#94A3B8',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
                  e.currentTarget.style.color = '#FFFFFF';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.color = '#94A3B8';
                }}
              >
                <RefreshCw size={14} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  color: '#94A3B8',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
                  e.currentTarget.style.color = '#FFFFFF';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.color = '#94A3B8';
                }}
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Body Content */}
          <div style={{
            flex: 1,
            padding: '16px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            scrollbarColor: 'rgba(139, 92, 246, 0.3) transparent',
            scrollbarWidth: 'thin'
          }}>
            {/* HERO WELCOME VIEW (Hostinger Agent Style with 1 Primary Card + Divider + 4 Grid Cards) */}
            {messages.length <= 1 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', paddingBottom: '4px' }}>
                {/* Hero Header */}
                <div style={{ padding: '4px 2px 2px 2px' }}>
                  <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    background: 'rgba(139, 92, 246, 0.15)',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    color: '#C4B5FD',
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '3px 10px',
                    borderRadius: '20px',
                    marginBottom: '8px'
                  }}>
                    <Sparkles size={12} color="#A78BFA" />
                    <span>AI Assistant</span>
                  </div>
                  <h3 style={{
                    color: '#FFFFFF',
                    fontSize: '18.5px',
                    fontWeight: 800,
                    margin: '0 0 6px 0',
                    lineHeight: '1.3',
                    letterSpacing: '-0.3px'
                  }}>
                    {roleConfig.welcomeTitle}
                  </h3>
                  <p style={{
                    color: '#94A3B8',
                    fontSize: '12px',
                    margin: 0,
                    lineHeight: '1.45'
                  }}>
                    {roleConfig.welcomeSubtitle}
                  </p>
                </div>

                {/* 1 Large Primary Featured Action Card */}
                {roleConfig.primaryCard && (
                  <div
                    onClick={() => handleSendMessage(roleConfig.primaryCard.query)}
                    style={{
                      background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.22) 0%, rgba(79, 70, 229, 0.14) 100%)',
                      border: '1.5px solid rgba(167, 139, 250, 0.38)',
                      borderRadius: '16px',
                      padding: '14px 16px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      boxShadow: '0 8px 24px rgba(124, 58, 237, 0.18)',
                      transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(124, 58, 237, 0.32) 0%, rgba(79, 70, 229, 0.22) 100%)';
                      e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.65)';
                      e.currentTarget.style.boxShadow = '0 12px 30px rgba(124, 58, 237, 0.3)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(124, 58, 237, 0.22) 0%, rgba(79, 70, 229, 0.14) 100%)';
                      e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.38)';
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(124, 58, 237, 0.18)';
                    }}
                  >
                    <div style={{
                      background: 'rgba(139, 92, 246, 0.25)',
                      width: '40px',
                      height: '40px',
                      borderRadius: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      {roleConfig.primaryCard.icon}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ color: '#FFFFFF', fontWeight: 700, fontSize: '13.5px', letterSpacing: '-0.1px' }}>
                        {roleConfig.primaryCard.title}
                      </div>
                      <div style={{ color: '#A78BFA', fontSize: '11px', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {roleConfig.primaryCard.subtitle}
                      </div>
                    </div>
                    <div style={{
                      background: 'rgba(255, 255, 255, 0.08)',
                      borderRadius: '50%',
                      width: '26px',
                      height: '26px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#C4B5FD',
                      flexShrink: 0
                    }}>
                      <ChevronRight size={16} />
                    </div>
                  </div>
                )}

                {/* Divider: ─── and more ─── */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  margin: '2px 0'
                }}>
                  <div style={{ flex: 1, height: '1px', background: 'rgba(255, 255, 255, 0.08)' }}></div>
                  <span style={{ color: '#64748B', fontSize: '11px', fontWeight: 600, letterSpacing: '0.5px', textTransform: 'lowercase' }}>
                    and more
                  </span>
                  <div style={{ flex: 1, height: '1px', background: 'rgba(255, 255, 255, 0.08)' }}></div>
                </div>

                {/* 4 Sleek Action Cards in 2x2 Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '10px'
                }}>
                  {roleConfig.gridCards.map((card, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSendMessage(card.query)}
                      style={{
                        background: 'rgba(255, 255, 255, 0.035)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '14px',
                        padding: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        transition: 'all 0.22s cubic-bezier(0.16, 1, 0.3, 1)'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.background = 'rgba(139, 92, 246, 0.12)';
                        e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.38)';
                        e.currentTarget.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.3)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.035)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        width: '28px',
                        height: '28px',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        {card.icon}
                      </div>
                      <div>
                        <div style={{ color: '#F1F5F9', fontWeight: 700, fontSize: '12.5px', lineHeight: '1.25' }}>
                          {card.title}
                        </div>
                        <div style={{ color: '#94A3B8', fontSize: '10.5px', marginTop: '2px', lineHeight: '1.3' }}>
                          {card.subtitle}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Conversation Messages Feed */}
            {messages.length > 1 && messages.slice(1).map(msg => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  gap: '5px'
                }}
              >
                <div style={{
                  maxWidth: '88%',
                  padding: '11px 15px',
                  borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  background: msg.role === 'user' 
                    ? 'linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%)' 
                    : 'rgba(255, 255, 255, 0.05)',
                  color: msg.role === 'user' ? '#FFFFFF' : '#E2E8F0',
                  fontSize: '13px',
                  lineHeight: '1.55',
                  boxShadow: msg.role === 'user' 
                    ? '0 4px 14px rgba(124, 58, 237, 0.35)' 
                    : '0 4px 16px rgba(0, 0, 0, 0.25)',
                  border: msg.role === 'user' ? 'none' : '1px solid rgba(255, 255, 255, 0.09)',
                  backdropFilter: 'blur(10px)'
                }}>
                  {msg.role === 'user' ? msg.content : renderFormattedContent(msg.content)}
                </div>

                {msg.toolUsed && (
                  <div style={{ fontSize: '10.5px', color: '#34D399', display: 'flex', alignItems: 'center', gap: '4px', paddingLeft: '4px' }}>
                    <CheckCircle2 size={12} color="#34D399" />
                    <span>Verified in DB ({msg.toolUsed.replace(/_/g, ' ')})</span>
                  </div>
                )}
              </div>
            ))}

            {/* Loading / Thinking Bar */}
            {loading && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: '#C4B5FD',
                fontSize: '12px',
                background: 'rgba(139, 92, 246, 0.12)',
                border: '1px solid rgba(139, 92, 246, 0.25)',
                padding: '8px 14px',
                borderRadius: '12px',
                width: 'fit-content'
              }}>
                <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite', color: '#A78BFA' }} />
                <span>AURA Copilot is checking live records...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestion Pills Bar (Visible during active conversation) */}
          {messages.length > 1 && (
            <div style={{
              padding: '8px 14px',
              background: 'rgba(10, 7, 22, 0.6)',
              borderTop: '1px solid rgba(255, 255, 255, 0.05)',
              display: 'flex',
              gap: '6px',
              overflowX: 'auto',
              whiteSpace: 'nowrap',
              scrollbarWidth: 'none'
            }}>
              {roleConfig.suggestions.map((sug, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(sug)}
                  style={{
                    background: 'rgba(139, 92, 246, 0.1)',
                    border: '1px solid rgba(139, 92, 246, 0.25)',
                    color: '#DDD6FE',
                    borderRadius: '20px',
                    padding: '5px 11px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    transition: 'all 0.15s'
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(139, 92, 246, 0.22)';
                    e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.5)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(139, 92, 246, 0.1)';
                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.25)';
                  }}
                >
                  <Sparkles size={11} color="#A78BFA" /> {sug}
                </button>
              ))}
            </div>
          )}

          {/* Floating Input Bar (Hostinger Style with circular upward arrow send button) */}
          <div style={{
            padding: '10px 14px 12px 14px',
            background: 'rgba(10, 7, 22, 0.9)',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <form
              onSubmit={e => { e.preventDefault(); handleSendMessage(); }}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '16px',
                display: 'flex',
                alignItems: 'center',
                padding: '4px 6px 4px 14px',
                transition: 'border-color 0.2s, box-shadow 0.2s'
              }}
              onFocus={e => {
                e.currentTarget.style.borderColor = '#8B5CF6';
                e.currentTarget.style.boxShadow = '0 0 14px rgba(139, 92, 246, 0.25)';
              }}
              onBlur={e => {
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <input
                type="text"
                value={inputMessage}
                onChange={e => setInputMessage(e.target.value)}
                placeholder="Ask a question or search records..."
                disabled={loading}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  fontSize: '13px',
                  color: '#FFFFFF',
                  outline: 'none',
                  padding: '6px 0'
                }}
              />
              <button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                title="Send message"
                style={{
                  background: inputMessage.trim() 
                    ? 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)' 
                    : 'rgba(255, 255, 255, 0.08)',
                  color: inputMessage.trim() ? '#FFFFFF' : '#64748B',
                  border: 'none',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: inputMessage.trim() ? 'pointer' : 'default',
                  transition: 'all 0.2s',
                  boxShadow: inputMessage.trim() ? '0 2px 8px rgba(139, 92, 246, 0.4)' : 'none',
                  flexShrink: 0
                }}
              >
                <ArrowUp size={16} strokeWidth={2.5} />
              </button>
            </form>

            <div style={{
              fontSize: '9.5px',
              color: '#64748B',
              textAlign: 'center',
              marginTop: '6px',
              letterSpacing: '0.1px'
            }}>
              AURA Copilot uses verified hospital database records.
            </div>
          </div>
        </div>
      )}
    </>
  );
}
