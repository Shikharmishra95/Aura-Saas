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
  t,
  patientData,
  patientPhone
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [showWelcomePopup, setShowWelcomePopup] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [activeCatIndex, setActiveCatIndex] = useState(0);
  const messagesEndRef = useRef(null);
  const widgetRef = useRef(null);
  const launcherRef = useRef(null);

  // Dynamic configuration for Role-Specific Hero Cards & Suggestions
  const getRoleConfig = () => {
    const role = (userRole || 'STAFF').toUpperCase();
    const hospName = activeHospital?.name || 'AURA Hospital';
    const hour = new Date().getHours();
    const timeGreeting = hour < 12 ? 'Good morning' : (hour < 17 ? 'Good afternoon' : 'Good evening');
    const cleanUsername = username ? (username.startsWith('Dr.') ? username : `Dr. ${username}`) : 'Doctor';
    const adminName = username ? (username.toLowerCase().startsWith('admin') ? username : `Admin ${username}`) : 'Admin';

    if (role === 'DOCTOR') {
      return {
        welcomeTitle: `${timeGreeting}, ${cleanUsername}! 🩺`,
        welcomeSubtitle: `I'm your Clinical Copilot for ${hospName}. Check your live queue, consultations, OPD earnings, or shifts in seconds.`,
        statusPill: `Doctor Portal Active • ${hospName}`,
        primaryCard: {
          icon: <Users size={20} color="#C4B5FD" />,
          title: "Show My Live Waiting Room Queue",
          subtitle: "Live OPD tokens, waiting list & patient complaints",
          query: "How many patients are waiting in my queue?"
        },
        categories: [
          {
            id: 'queue',
            label: '👥 My Queue',
            cards: [
              {
                icon: <Users size={16} color="#C4B5FD" />,
                title: "Live Waiting Room Queue",
                subtitle: "Current tokens & waiting count",
                query: "How many patients are waiting in my queue?"
              },
              {
                icon: <Stethoscope size={16} color="#34D399" />,
                title: "Next Patient's Complaint",
                subtitle: "Chief symptoms & medical intake",
                query: "What is the next patient's chief complaint?"
              },
              {
                icon: <CheckCircle2 size={16} color="#38BDF8" />,
                title: "Consulted Patients Today",
                subtitle: "Completed consultation count",
                query: "Today's total consulted patients"
              }
            ]
          },
          {
            id: 'schedule',
            label: '⏰ Schedule & Leave',
            cards: [
              {
                icon: <Clock size={16} color="#A78BFA" />,
                title: "My Shift Timings Tomorrow",
                subtitle: "OPD hours & duty schedule",
                query: "What are my shift timings for tomorrow?"
              },
              {
                icon: <Palmtree size={16} color="#F472B6" />,
                title: "Check Leave Request Status",
                subtitle: "Approved upcoming leaves",
                query: "Check my approved leave status"
              },
              {
                icon: <Calendar size={16} color="#FBBF24" />,
                title: "Weekly Shift Roster",
                subtitle: "My schedule for this week",
                query: "Show my doctor schedule this week"
              }
            ]
          },
          {
            id: 'earnings',
            label: '💰 OPD Earnings',
            cards: [
              {
                icon: <DollarSign size={16} color="#FBBF24" />,
                title: "My OPD Earnings Today",
                subtitle: "Consultation revenue & fee count",
                query: "What are my OPD earnings today?"
              },
              {
                icon: <TrendingUp size={16} color="#34D399" />,
                title: "Monthly Consultation Stats",
                subtitle: "Total visits consulted this month",
                query: "My monthly consultation stats"
              }
            ]
          }
        ],
        suggestions: [
          "How many patients are waiting in my queue?",
          "What is the next patient's chief complaint?",
          "What are my shift timings for tomorrow?",
          "Check my approved leave status",
          "Today's total consulted patients",
          "What are my OPD earnings today?"
        ],
        popupItems: [
          { icon: '👥', title: 'Live Waiting Queue', query: 'How many patients are waiting in my queue?' },
          { icon: '🩺', title: "Next Patient's Complaint", query: "What is the next patient's chief complaint?" },
          { icon: '⏰', title: 'My Shift Timings Tomorrow', query: 'What are my shift timings for tomorrow?' },
          { icon: '💰', title: 'My OPD Earnings Today', query: 'What are my OPD earnings today?' }
        ]
      };
    }

    if (role === 'ADMIN' || role === 'HOSPITAL_ADMIN') {
      return {
        welcomeTitle: `${timeGreeting}, ${adminName}! 👋`,
        welcomeSubtitle: `Executive Hospital Copilot for ${hospName}. Real-time intelligence across OPD collections, doctor duty rosters, and appointment status.`,
        statusPill: `Live Hospital Node • Live DB Grounded`,
        primaryCard: {
          icon: <TrendingUp size={20} color="#C4B5FD" />,
          title: "Monthly OPD Revenue & Dues Overview",
          subtitle: "Total collections, dues, and payment metrics",
          query: "What is our total OPD revenue for this month?"
        },
        categories: [
          {
            id: 'finance',
            label: '💰 Finance',
            cards: [
              {
                icon: <DollarSign size={16} color="#34D399" />,
                title: "Monthly OPD Revenue",
                subtitle: "Total collected vs pending balance",
                query: "What is our total OPD revenue for this month?"
              },
              {
                icon: <Activity size={16} color="#FBBF24" />,
                title: "Today's Cash vs UPI",
                subtitle: "Front desk payment breakdown",
                query: "Today's total revenue and dues collection"
              },
              {
                icon: <TrendingUp size={16} color="#A78BFA" />,
                title: "Pending Collection Dues",
                subtitle: "Uncollected patient balance summary",
                query: "Pending collection dues summary"
              }
            ]
          },
          {
            id: 'doctors',
            label: '🩺 Doctors & Duty',
            cards: [
              {
                icon: <UserCheck size={16} color="#38BDF8" />,
                title: "Doctors on Duty Today",
                subtitle: "Active specialists & availability",
                query: "Which doctors are available and on duty today?"
              },
              {
                icon: <Clock size={16} color="#C4B5FD" />,
                title: "Doctor Shift Timings",
                subtitle: "Weekly OPD hours & consultation fee chart",
                query: "Show all doctor shift timings and OPD fees"
              },
              {
                icon: <Palmtree size={16} color="#FB7185" />,
                title: "Doctor Leave Status",
                subtitle: "Check approved leaves for today & tomorrow",
                query: "Which doctors are on leave today?"
              }
            ]
          },
          {
            id: 'operations',
            label: '⚠️ Operations & Status',
            cards: [
              {
                icon: <AlertCircle size={16} color="#F43F5E" />,
                title: "Cancelled Appointments",
                subtitle: "Today's cancellation count & reasons",
                query: "How many appointments were cancelled today?"
              },
              {
                icon: <Users size={16} color="#A78BFA" />,
                title: "Live OPD Queue Summary",
                subtitle: "Waiting tokens and patient load",
                query: "Show live OPD queue summary"
              },
              {
                icon: <FileText size={16} color="#FBBF24" />,
                title: "Missed / No-Show Visits",
                subtitle: "Patients who skipped consultation",
                query: "How many patients missed their visit today?"
              }
            ]
          },
          {
            id: 'analytics',
            label: '📊 Analytics & Plan',
            cards: [
              {
                icon: <TrendingUp size={16} color="#38BDF8" />,
                title: "Doctor Booking Matrix",
                subtitle: "Load & completion performance",
                query: "Show doctor-wise booking performance"
              },
              {
                icon: <ShieldCheck size={16} color="#34D399" />,
                title: "Hospital License Validity",
                subtitle: "SaaS subscription status & expiry",
                query: "What is our hospital subscription plan validity?"
              },
              {
                icon: <Building2 size={16} color="#C4B5FD" />,
                title: "Active Departments",
                subtitle: "Specialties & doctor count",
                query: "Show active departments and doctors directory"
              }
            ]
          }
        ],
        suggestions: [
          "How many appointments were cancelled today?",
          "What is our total OPD revenue for this month?",
          "Which doctors are available and on duty today?",
          "Show doctor-wise booking performance",
          "Pending collection dues summary"
        ],
        popupItems: [
          { icon: '💰', title: "Today's OPD Revenue", query: "Today's total OPD revenue collection?" },
          { icon: '🩺', title: 'Doctors on Duty Today', query: 'Which doctors are on duty today and available?' },
          { icon: '⚠️', title: "Cancelled Bookings Today", query: 'How many appointments were cancelled today?' },
          { icon: '💵', title: 'Pending Patient Dues', query: 'Show pending patient dues & unpaid bills' }
        ]
      };
    }

    if (role === 'SUPER_ADMIN' || role === 'SUPERADMIN') {
      return {
        welcomeTitle: `${timeGreeting}, SuperAdmin! 🌐`,
        welcomeSubtitle: `Global multi-tenant control tower. Monitor SaaS subscription collections, hospital fleets, and AI voice telemetry.`,
        statusPill: `Platform Control Tower Online`,
        primaryCard: {
          icon: <TrendingUp size={20} color="#C4B5FD" />,
          title: "Platform Monthly Revenue Overview",
          subtitle: "Total SaaS collections & subscription run-rate",
          query: "Platform monthly revenue overview"
        },
        categories: [
          {
            id: 'saas',
            label: '💳 SaaS Revenue',
            cards: [
              {
                icon: <TrendingUp size={16} color="#A78BFA" />,
                title: "Platform Monthly Revenue",
                subtitle: "Global SaaS subscription collections",
                query: "Platform monthly revenue overview"
              },
              {
                icon: <Clock size={16} color="#FBBF24" />,
                title: "Expiring Plans (30 Days)",
                subtitle: "Tenant renewals requiring action",
                query: "Which subscriptions are expiring in next 30 days?"
              },
              {
                icon: <DollarSign size={16} color="#34D399" />,
                title: "Top Revenue Hospital",
                subtitle: "Highest SaaS revenue contributor",
                query: "Which hospital generates maximum revenue?"
              }
            ]
          },
          {
            id: 'fleet',
            label: '🏢 Hospital Tenants',
            cards: [
              {
                icon: <Building2 size={16} color="#C4B5FD" />,
                title: "Active Hospitals Count",
                subtitle: "Total onboarded tenant clinics",
                query: "How many hospitals are active on AURA platform?"
              },
              {
                icon: <ShieldCheck size={16} color="#38BDF8" />,
                title: "Tenant Roster Directory",
                subtitle: "Hospital tiers, doctors & plan status",
                query: "Show all active hospital tenants"
              },
              {
                icon: <Activity size={16} color="#FB7185" />,
                title: "System Error Telemetry",
                subtitle: "Platform error logs & audit",
                query: "Show platform error telemetry"
              }
            ]
          },
          {
            id: 'telephony',
            label: '🎙️ AI Voice Traffic',
            cards: [
              {
                icon: <Activity size={16} color="#34D399" />,
                title: "Voice AI Calls Today",
                subtitle: "Total telephony volume processed",
                query: "Total AI voice calls processed today"
              },
              {
                icon: <Clock size={16} color="#A78BFA" />,
                title: "Call Telemetry Breakdown",
                subtitle: "Per-hospital voice call distribution",
                query: "Total AI voice calls processed"
              },
              {
                icon: <ShieldCheck size={16} color="#38BDF8" />,
                title: "Security Audit Trail",
                subtitle: "Administrative log trace",
                query: "Show security audit trail"
              }
            ]
          }
        ],
        suggestions: [
          "Platform monthly revenue overview",
          "How many hospitals are active on AURA platform?",
          "Which subscriptions are expiring in next 30 days?",
          "Total AI voice calls processed today"
        ],
        popupItems: [
          { icon: '💳', title: 'Platform Monthly Revenue', query: 'Platform monthly revenue overview' },
          { icon: '🏢', title: 'Active Hospitals Count', query: 'How many hospitals are active on AURA platform?' },
          { icon: '⏳', title: 'Expiring Plans (30 Days)', query: 'Which subscriptions are expiring in next 30 days?' },
          { icon: '🎙️', title: 'Voice AI Calls Today', query: 'Total AI voice calls processed today' }
        ]
      };
    }

    if (role === 'PATIENT') {
      return {
        welcomeTitle: `${timeGreeting}! Welcome to ${hospName}`,
        welcomeSubtitle: `I am your personal AI healthcare assistant. Book appointments, check doctor OPD hours, and view queue status in seconds.`,
        statusPill: `Patient Health Desk Online`,
        primaryCard: {
          icon: <Calendar size={20} color="#38BDF8" />,
          title: "Book Doctor Appointment",
          subtitle: "Quick OPD consultation booking",
          query: "I want to book an appointment"
        },
        categories: [
          {
            id: 'booking',
            label: '📅 Bookings & Queue',
            cards: [
              {
                icon: <Calendar size={16} color="#38BDF8" />,
                title: "Book Doctor Appointment",
                subtitle: "Select doctor, date & time slot",
                query: "I want to book an appointment"
              },
              {
                icon: <Activity size={16} color="#34D399" />,
                title: "Live Token Position",
                subtitle: "Check waiting status in OPD queue",
                query: "Check my live token position"
              },
              {
                icon: <FileText size={16} color="#F472B6" />,
                title: "My Booked Appointments",
                subtitle: "View your upcoming visits",
                query: "Show my booked appointments"
              }
            ]
          },
          {
            id: 'doctors',
            label: '🩺 Doctors & Fees',
            cards: [
              {
                icon: <UserCheck size={16} color="#C4B5FD" />,
                title: "Doctors on Duty Today",
                subtitle: "Find available OPD specialists",
                query: "Which doctors are available today?"
              },
              {
                icon: <Clock size={16} color="#FBBF24" />,
                title: "Doctor Consultation Fees",
                subtitle: "OPD charges and doctor timings",
                query: "What are the doctor consultation fees?"
              },
              {
                icon: <ShieldCheck size={16} color="#38BDF8" />,
                title: "Insurance & TPA Panels",
                subtitle: "Cashless tie-ups supported",
                query: "What insurance TPA panels are supported?"
              }
            ]
          }
        ],
        suggestions: [
          "I want to book an appointment",
          "Which doctors are available today?",
          "Check my live token position",
          "What are the doctor consultation fees?",
          "Show my booked appointments"
        ],
        popupItems: [
          { icon: '📅', title: 'Book Doctor Appointment', query: 'I want to book an appointment' },
          { icon: '🩺', title: 'Available Doctors Today', query: 'Which doctors are available today?' },
          { icon: '🎫', title: 'Check My Token Status', query: 'Check my live token position' },
          { icon: '💵', title: 'Doctor Consultation Fees', query: 'What are the doctor consultation fees?' }
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
      ],
      popupItems: [
        { icon: '👥', title: "Today's OPD Queue Summary", query: "Today's OPD Queue Summary" },
        { icon: '🩺', title: 'Doctors on Duty Today', query: 'Which doctors are on duty today?' },
        { icon: '⚠️', title: 'Cancelled Appointments Today', query: 'How many appointments were cancelled today?' },
        { icon: '💵', title: 'Fees & Shift Timings', query: 'Show all doctor shift timings and OPD fees' }
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
  }, [messages, loading, isOpen]);

  // Role & Hospital scoped session key for proactive popup
  const popupDismissKey = `aura_popup_dismissed_${(userRole || 'STAFF').toUpperCase()}_${activeHospital?.id || 'GLOBAL'}`;

  // Proactive Welcome Popup: Show 1.2s after login/role-switch if not dismissed in session for this portal
  useEffect(() => {
    const isDismissed = sessionStorage.getItem(popupDismissKey);
    if (!isDismissed && !isOpen) {
      const timer = setTimeout(() => {
        setShowWelcomePopup(true);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [token, userRole, activeHospital?.id]);

  // Hide proactive popup if user manually opens copilot
  useEffect(() => {
    if (isOpen) {
      setShowWelcomePopup(false);
    }
  }, [isOpen]);

  // Click outside on main screen to minimize / collapse copilot (maintaining full conversation state)
  useEffect(() => {
    function handleClickOutside(event) {
      if (!isOpen || !widgetRef.current) return;
      // If click was inside the chat window, don't close
      if (widgetRef.current.contains(event.target)) return;
      // If click was on launcher button, don't close
      if (launcherRef.current && launcherRef.current.contains(event.target)) return;

      // Clicked outside on the portal screen - minimize immediately
      setIsOpen(false);
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isOpen]);

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
      const portalSlug = activeHospital?.slug || (window.location.pathname.startsWith('/portal/') ? window.location.pathname.split('/')[2] : null);
      const reqHeaders = {
        'Content-Type': 'application/json'
      };
      if (token && token !== 'null' && token !== 'undefined') {
        reqHeaders['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch('/api/v1/copilot/chat', {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
          active_tab: activeTab || 'overview',
          selected_date: selectedDate || '',
          hospital_id: activeHospital?.id || null,
          slug: portalSlug,
          patient_name: patientData?.name || username || null,
          patient_phone: patientPhone || patientData?.phone || null,
          patient_data: patientData || null
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
          toolUsed: data.tool_used,
          suggestions: data.suggestions || []
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
      {/* Proactive Floating Welcome Card / Speech Bubble (Big Companies Style) */}
      {!isOpen && showWelcomePopup && (
        <div 
          style={{
            position: 'fixed',
            bottom: '80px',
            right: '24px',
            width: '320px',
            background: 'linear-gradient(145deg, rgba(20, 14, 40, 0.98) 0%, rgba(10, 7, 24, 0.98) 100%)',
            border: '1.5px solid rgba(139, 92, 246, 0.45)',
            borderRadius: '20px',
            padding: '16px',
            boxShadow: '0 20px 45px -10px rgba(0, 0, 0, 0.85), 0 0 25px rgba(124, 58, 237, 0.3)',
            zIndex: 9997,
            backdropFilter: 'blur(16px)',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            animation: 'fadeSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
          }}
        >
          {/* Top Bar: Avatar, Title, Close X */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                background: 'linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)',
                width: '28px',
                height: '28px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 10px rgba(124, 58, 237, 0.6)'
              }}>
                <Sparkles size={14} color="#FFFFFF" />
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span>AURA Copilot</span>
                  <span style={{ fontSize: '9px', fontWeight: 700, color: '#A78BFA', background: 'rgba(139, 92, 246, 0.2)', padding: '1px 5px', borderRadius: '4px' }}>AI</span>
                </div>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowWelcomePopup(false);
                sessionStorage.setItem(popupDismissKey, 'true');
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94A3B8',
                cursor: 'pointer',
                padding: '3px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Dismiss"
            >
              <X size={15} />
            </button>
          </div>

          {/* Greeting & Intro */}
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginBottom: '4px' }}>
            {roleConfig.welcomeTitle.split('!')[0]}! 👋
          </div>
          <div style={{ fontSize: '11.5px', color: '#94A3B8', marginBottom: '12px', lineHeight: '1.4' }}>
            I can help you with live records right now:
          </div>

          {/* Capability Quick Chips (Role Specific) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
            {(roleConfig.popupItems || []).map((item, pIdx) => (
              <button
                key={pIdx}
                onClick={() => {
                  setShowWelcomePopup(false);
                  sessionStorage.setItem(popupDismissKey, 'true');
                  setIsOpen(true);
                  handleSendMessage(item.query);
                }}
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  padding: '7px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: '#DDD6FE',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.18s'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(139, 92, 246, 0.2)';
                  e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.4)';
                  e.currentTarget.style.color = '#FFFFFF';
                  e.currentTarget.style.transform = 'translateX(2px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                  e.currentTarget.style.color = '#DDD6FE';
                  e.currentTarget.style.transform = 'translateX(0)';
                }}
              >
                <span style={{ fontSize: '13px' }}>{item.icon}</span>
                <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.title}</span>
                <ChevronRight size={13} color="#A78BFA" />
              </button>
            ))}
          </div>

          {/* Open Full Copilot Button */}
          <button
            onClick={() => {
              setShowWelcomePopup(false);
              sessionStorage.setItem(popupDismissKey, 'true');
              setIsOpen(true);
            }}
            style={{
              width: '100%',
              background: 'linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '12px',
              padding: '8px 12px',
              fontSize: '12px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)',
              transition: 'all 0.2s'
            }}
          >
            <Sparkles size={13} />
            <span>Open Copilot & Ask Anything</span>
          </button>

          {/* Pointer Arrow down to launcher */}
          <div style={{
            position: 'absolute',
            bottom: '-7px',
            right: '40px',
            width: '14px',
            height: '14px',
            background: 'rgba(10, 7, 24, 0.98)',
            borderRight: '1.5px solid rgba(139, 92, 246, 0.45)',
            borderBottom: '1.5px solid rgba(139, 92, 246, 0.45)',
            transform: 'rotate(45deg)'
          }} />
        </div>
      )}

      {/* Floating Action Button (Hostinger Glowing Obsidian Badge) */}
      {!isOpen && (
        <button
          ref={launcherRef}
          onClick={() => {
            setShowWelcomePopup(false);
            setIsOpen(true);
          }}
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
        <div 
          ref={widgetRef}
          style={{
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
                  <span>Online</span> • <span style={{ color: '#CBD5E1', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{role === 'SUPER_ADMIN' ? 'Platform Control Tower' : (activeHospital?.name || 'Hospital')}</span>
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
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginBottom: '8px',
                    flexWrap: 'wrap'
                  }}>
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
                      borderRadius: '20px'
                    }}>
                      <Sparkles size={12} color="#A78BFA" />
                      <span>Executive AI</span>
                    </div>

                    {roleConfig.statusPill && (
                      <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: 'rgba(34, 197, 94, 0.1)',
                        border: '1px solid rgba(34, 197, 94, 0.25)',
                        color: '#86EFAC',
                        fontSize: '10.5px',
                        fontWeight: 600,
                        padding: '2px 9px',
                        borderRadius: '20px'
                      }}>
                        <span style={{ display: 'inline-block', width: '5px', height: '5px', borderRadius: '50%', background: '#22C55E', boxShadow: '0 0 5px #22C55E' }}></span>
                        <span>{roleConfig.statusPill}</span>
                      </div>
                    )}
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

                {/* Divider: ─── Categorized Executive Questions ─── */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  margin: '2px 0'
                }}>
                  <div style={{ flex: 1, height: '1px', background: 'rgba(255, 255, 255, 0.08)' }}></div>
                  <span style={{ color: '#A78BFA', fontSize: '11px', fontWeight: 700, letterSpacing: '0.4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Sparkles size={11} color="#A78BFA" />
                    <span>Frequently Asked Questions</span>
                  </span>
                  <div style={{ flex: 1, height: '1px', background: 'rgba(255, 255, 255, 0.08)' }}></div>
                </div>

                {/* If Categories Exist (Big Companies Salesforce/Microsoft Style) */}
                {roleConfig.categories && roleConfig.categories.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {/* Category Navigation Pills */}
                    <div style={{
                      display: 'flex',
                      gap: '6px',
                      overflowX: 'auto',
                      paddingBottom: '3px',
                      scrollbarWidth: 'none'
                    }}>
                      {roleConfig.categories.map((cat, cIdx) => {
                        const isSelected = activeCatIndex === cIdx;
                        return (
                          <button
                            key={cat.id || cIdx}
                            onClick={() => setActiveCatIndex(cIdx)}
                            style={{
                              background: isSelected 
                                ? 'linear-gradient(135deg, rgba(124, 58, 237, 0.35) 0%, rgba(79, 70, 229, 0.25) 100%)' 
                                : 'rgba(255, 255, 255, 0.04)',
                              border: isSelected 
                                ? '1.5px solid rgba(167, 139, 250, 0.7)' 
                                : '1px solid rgba(255, 255, 255, 0.08)',
                              borderRadius: '20px',
                              color: isSelected ? '#FFFFFF' : '#94A3B8',
                              padding: '5px 12px',
                              fontSize: '11.5px',
                              fontWeight: isSelected ? 700 : 500,
                              cursor: 'pointer',
                              whiteSpace: 'nowrap',
                              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                              boxShadow: isSelected ? '0 4px 14px rgba(124, 58, 237, 0.3)' : 'none'
                            }}
                          >
                            {cat.label}
                          </button>
                        );
                      })}
                    </div>

                    {/* Active Category Cards */}
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px'
                    }}>
                      {(roleConfig.categories[activeCatIndex] || roleConfig.categories[0])?.cards.map((card, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleSendMessage(card.query)}
                          style={{
                            background: 'rgba(255, 255, 255, 0.035)',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            borderRadius: '13px',
                            padding: '10px 14px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
                          }}
                          onMouseEnter={e => {
                            e.currentTarget.style.transform = 'translateX(3px)';
                            e.currentTarget.style.background = 'rgba(139, 92, 246, 0.12)';
                            e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.45)';
                          }}
                          onMouseLeave={e => {
                            e.currentTarget.style.transform = 'translateX(0)';
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.035)';
                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                          }}
                        >
                          <div style={{
                            background: 'rgba(139, 92, 246, 0.2)',
                            width: '32px',
                            height: '32px',
                            borderRadius: '9px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0
                          }}>
                            {card.icon}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ color: '#F1F5F9', fontWeight: 700, fontSize: '12.5px' }}>
                              {card.title}
                            </div>
                            <div style={{ color: '#94A3B8', fontSize: '11px', marginTop: '1px' }}>
                              {card.subtitle}
                            </div>
                          </div>
                          <ChevronRight size={15} color="#A78BFA" />
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  /* Fallback to gridCards if no categories */
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '10px'
                  }}>
                    {roleConfig.gridCards && roleConfig.gridCards.map((card, idx) => (
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
                )}
              </div>
            ) : null}

            {/* Conversation Messages Feed */}
            {messages.length > 1 && messages.slice(1).map((msg, index, arr) => {
              const isLatestAssistant = msg.role === 'assistant' && index === arr.length - 1;
              return (
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

                  {/* Suggestion Question Pills: ALWAYS show pills strictly related to user's question on the latest assistant response */}
                  {isLatestAssistant && !loading && msg.suggestions && msg.suggestions.length > 0 && (
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '6px',
                      marginTop: '6px',
                      maxWidth: '96%'
                    }}>
                      {msg.suggestions.map((sug, sIdx) => (
                        <button
                          key={sIdx}
                          onClick={() => handleSendMessage(sug)}
                          style={{
                            background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(79, 70, 229, 0.14) 100%)',
                            border: '1px solid rgba(167, 139, 250, 0.45)',
                            borderRadius: '16px',
                            color: '#EDE9FE',
                            padding: '5px 12px',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            transition: 'all 0.18s',
                            textAlign: 'left'
                          }}
                          onMouseEnter={e => {
                            e.currentTarget.style.background = 'linear-gradient(135deg, rgba(124, 58, 237, 0.38) 0%, rgba(79, 70, 229, 0.28) 100%)';
                            e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.8)';
                            e.currentTarget.style.color = '#FFFFFF';
                            e.currentTarget.style.transform = 'translateY(-1px)';
                          }}
                          onMouseLeave={e => {
                            e.currentTarget.style.background = 'linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(79, 70, 229, 0.14) 100%)';
                            e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.45)';
                            e.currentTarget.style.color = '#EDE9FE';
                            e.currentTarget.style.transform = 'translateY(0)';
                          }}
                        >
                          <Sparkles size={11} color="#A78BFA" />
                          <span>{sug}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

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
