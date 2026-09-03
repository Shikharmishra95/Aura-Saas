import React, { useState } from 'react';
import { Eye, EyeOff, Shield, UserPlus, Heart, Sliders, CreditCard, Sparkles, CheckCircle2 } from 'lucide-react';

export default function LoginPage({
  loginRole,
  setLoginRole,
  loginUsername,
  setLoginUsername,
  loginPassword,
  setLoginPassword,
  showLoginPassword,
  setShowLoginPassword,
  loginError,
  handleLogin,
  showRegisterHospital,
  setShowRegisterHospital,
  hospName,
  setHospName,
  hospPhone,
  setHospPhone,
  hospAddress,
  setHospAddress,
  hospAdminUsername,
  setHospAdminUsername,
  hospAdminEmail,
  setHospAdminEmail,
  hospAdminPassword,
  setHospAdminPassword,
  selectedPlan,
  setSelectedPlan,
  onboardError,
  onboardSuccess,
  handleRegisterHospital,
  t
}) {
  const [pageView, setPageView] = useState(() => {
    if (localStorage.getItem('redirect_login')) {
      localStorage.removeItem('redirect_login');
      return 'login';
    }
    return 'landing';
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const scrollToSection = (id) => {
    if (pageView !== 'landing') {
      setPageView('landing');
      setTimeout(() => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSelectPlanAndOnboard = (planId) => {
    setSelectedPlan(planId);
    setPageView('onboard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const loadRazorpay = () => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleOpenCheckout = async (e) => {
    e.preventDefault();
    if (!hospName || !hospPhone || !hospAdminUsername || !hospAdminEmail || !hospAdminPassword) {
      alert("Please fill all required fields before proceeding to payment.");
      return;
    }

    let planAmount = 2999; // PRO Plan
    if (selectedPlan === 'ENTERPRISE') planAmount = 29999;
    if (selectedPlan === 'STARTER' || selectedPlan === 'BASIC') planAmount = 0;

    if (planAmount === 0) {
      await handleConfirmPaymentAndOnboard();
      return;
    }

    const loaded = await loadRazorpay();
    if (!loaded) {
      alert("Failed to load Razorpay Payment Gateway. Please check your internet connection.");
      return;
    }

    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY_ID || "rzp_test_TDfSGFZwtVgpme",
      amount: planAmount * 100, // Amount in paise
      currency: "INR",
      name: hospName || "AURA SaaS Hospital Platform",
      description: `Hospital Subscription (${selectedPlan || 'PRO'} Plan)`,
      image: "https://cdn-icons-png.flaticon.com/512/2966/2966327.png",
      prefill: {
        name: hospAdminUsername || "Hospital Admin",
        email: hospAdminEmail || "admin@hospital.com",
        contact: hospPhone || "9532399202"
      },
      theme: {
        color: "#2563EB"
      },
      modal: {
        ondismiss: function() {
          console.log("Razorpay Checkout dismissed by user.");
        }
      },
      handler: async function (response) {
        console.log("Razorpay Subscription Payment Success:", response);
        await handleConfirmPaymentAndOnboard(response.razorpay_payment_id);
      }
    };

    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const handleConfirmPaymentAndOnboard = async (paymentId = null) => {
    setIsSubmitting(true);
    try {
      const savedAdminUsername = hospAdminUsername;
      const savedAdminPassword = hospAdminPassword;
      const fakeEvent = { preventDefault: () => {} };
      await handleRegisterHospital(fakeEvent);

      setIsSubmitting(false);

      setLoginUsername(savedAdminUsername);
      setLoginPassword(savedAdminPassword);
      setLoginRole('ADMIN');
      setPageView('login');

      alert(`🎉 Registration & Subscription Activated!\nYour Hospital Account (${hospName}) has been onboarded successfully.\nSign in now using Admin Username: '${savedAdminUsername}'`);
    } catch (err) {
      setIsSubmitting(false);
      const isDuplicate = (err.message || '').toLowerCase().includes('already registered') || (err.message || '').toLowerCase().includes('already exists');
      if (isDuplicate) {
        alert(`⚠️ Account Notice: ${err.message}\n\nRedirecting you to the Login screen to sign in.`);
        setLoginUsername(hospAdminUsername || '');
        setLoginPassword('');
        setLoginRole('ADMIN');
        setPageView('login');
      } else {
        alert("Registration Error: " + err.message);
      }
    }
  };

  const handleQuickFill = (u, p, r) => {
    setLoginUsername(u);
    setLoginPassword(p);
    setLoginRole(r);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(180deg, #F0F4FA 0%, #E6EEF8 100%)', color: '#0F172A', display: 'flex', flexDirection: 'column', overflowX: 'hidden' }}>
      
      {/* ── SINGLE CLEAN SAAS NAVBAR ── */}
      <header style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '16px 40px', background: 'rgba(255, 255, 255, 0.95)', backdropFilter: 'blur(16px)',
        borderBottom: '2px solid #DBEAFE', boxShadow: '0 4px 20px rgba(37, 99, 235, 0.06)', position: 'sticky', top: 0, zIndex: 100
      }}>
        {/* Brand Logo */}
        <div 
          onClick={() => setPageView('landing')}
          style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}
        >
          <div className="pulse-glow-box" style={{
            width: '42px', height: '42px', borderRadius: '12px',
            background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#FFFFFF', fontSize: '22px', fontWeight: 800
          }}>
            ⚡
          </div>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', margin: 0, lineHeight: 1.1 }}>
              AURA <span style={{ color: '#2563EB' }}>SaaS</span>
            </h1>
            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 700 }}>
              AI Hospital Management Platform
            </div>
          </div>
        </div>

        {/* Nav Links & Sign In Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <button onClick={() => scrollToSection('pricing')} style={{ background: 'none', border: 'none', color: '#475569', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}>
            📊 Pricing Plans
          </button>
          <button onClick={() => scrollToSection('features')} style={{ background: 'none', border: 'none', color: '#475569', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}>
            ✨ Features
          </button>
          <button 
            onClick={() => setPageView('login')}
            style={{
              background: pageView === 'login' ? '#1E40AF' : 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
              color: '#FFFFFF', border: 'none',
              borderRadius: '10px', padding: '9px 24px', fontSize: '14px', fontWeight: 800,
              cursor: 'pointer', transition: 'all 0.25s',
              boxShadow: pageView === 'login' ? '0 4px 14px rgba(30,64,175,0.4)' : '0 4px 14px rgba(37,99,235,0.25)'
            }}
          >
            🔐 Sign In
          </button>
        </div>
      </header>

      {/* ── VIEW 1: LANDING HOMEPAGE (`pageView === 'landing'`) ── */}
      {pageView === 'landing' && (
        <div className="animate-slide-up">
          {/* Hero Section (Reverted 3-Step & 4 KPI Boxes as requested) */}
          <section id="hero" style={{ padding: '60px 20px 40px', textAlign: 'center', maxWidth: '950px', margin: '0 auto' }}>
            <span style={{ background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: '30px', padding: '6px 20px', fontSize: '13px', fontWeight: 800, display: 'inline-block', marginBottom: '18px' }}>
              🚀 NEXT-GEN AI VOICE HEALTHCARE PLATFORM
            </span>

            <h1 style={{ fontSize: '44px', fontWeight: 900, color: '#0F172A', lineHeight: 1.2, marginBottom: '18px', letterSpacing: '-0.8px' }}>
              Transform Your Hospital with <span style={{ color: '#2563EB', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI Voice Receptionist</span>
            </h1>
            
            <p style={{ fontSize: '16px', color: '#475569', fontWeight: 600, maxWidth: '760px', margin: '0 auto', lineHeight: 1.6 }}>
              AURA SaaS automates hospital patient calls, OPD scheduling, doctor consultation queues, WhatsApp medical prescriptions, & real-time revenue analytics in one unified multi-tenant platform. Select a subscription plan below to onboard your hospital instantly!
            </p>
          </section>

          {/* SaaS Pricing Plans Section (FIRST BELOW HERO) */}
          <section id="pricing" style={{ padding: '40px 20px 60px', background: '#F0F4FA', borderTop: '2px solid #DBEAFE' }}>
            <div style={{ maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
              <span style={{ color: '#2563EB', fontSize: '13px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                PRICING & SUBSCRIPTION PLANS
              </span>
              <h2 style={{ fontSize: '30px', fontWeight: 900, color: '#0F172A', margin: '6px 0 12px 0' }}>
                Choose Your Hospital Subscription Plan
              </h2>
              <p style={{ fontSize: '14px', color: '#64748B', maxWidth: '600px', margin: '0 auto 36px', fontWeight: 600 }}>
                Click any plan below to proceed directly to hospital onboarding.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', textAlign: 'left' }}>
                
                {/* Starter Plan */}
                <div className="pricing-card-hover" style={{ background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '22px', padding: '30px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 8px 24px rgba(15,23,42,0.04)' }}>
                  <div>
                    <div style={{ fontSize: '18px', fontWeight: 800, color: '#334155' }}>🥉 Starter Plan</div>
                    <div style={{ fontSize: '30px', fontWeight: 900, color: '#0F172A', margin: '12px 0 4px 0' }}>
                      15-Day Free <span style={{ fontSize: '14px', color: '#64748B', fontWeight: 600 }}>/ trial</span>
                    </div>
                    <p style={{ fontSize: '12px', color: '#64748B', marginBottom: '20px', fontWeight: 600 }}>Ideal for small single-doctor clinics exploring AI booking.</p>

                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#334155', fontWeight: 600 }}>
                      <li>✓ 👨‍⚕️ <strong>Max 1 Doctor</strong> Registration</li>
                      <li>✓ 🖥️ Full Receptionist Workspace</li>
                      <li>✓ 📱 Online Patient Portal Booking</li>
                      <li>❌ 🔒 <strong>AI Voice Helpline Locked</strong></li>
                    </ul>
                  </div>

                  <button 
                    onClick={() => handleSelectPlanAndOnboard('STARTER')}
                    style={{ width: '100%', padding: '13px', borderRadius: '12px', border: '1.5px solid #CBD5E1', background: '#F8FAFC', color: '#0F172A', fontWeight: 800, fontSize: '14px', cursor: 'pointer', marginTop: '24px', transition: 'all 0.2s' }}
                  >
                    Choose Starter Plan →
                  </button>
                </div>

                {/* Pro AI Plan */}
                <div className="pricing-card-hover" style={{ background: '#FFFFFF', border: '2.5px solid #2563EB', borderRadius: '22px', padding: '30px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 14px 36px rgba(37,99,235,0.18)', position: 'relative' }}>
                  <span style={{ position: 'absolute', top: '-14px', right: '24px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', color: '#FFFFFF', fontSize: '11px', fontWeight: 800, padding: '4px 14px', borderRadius: '20px', boxShadow: '0 4px 10px rgba(37,99,235,0.3)' }}>
                    MOST POPULAR
                  </span>
                  <div>
                    <div style={{ fontSize: '18px', fontWeight: 800, color: '#2563EB' }}>🥈 Pro AI Plan</div>
                    <div style={{ fontSize: '30px', fontWeight: 900, color: '#0F172A', margin: '12px 0 4px 0' }}>
                      ₹2,999 <span style={{ fontSize: '14px', color: '#64748B', fontWeight: 600 }}>/ month</span>
                    </div>
                    <p style={{ fontSize: '12px', color: '#64748B', marginBottom: '20px', fontWeight: 600 }}>Best for busy hospitals needing full AI Call & OPD automation.</p>

                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#334155', fontWeight: 600 }}>
                      <li>✓ 👨‍⚕️ <strong>Max 5 Doctors</strong> & 2 Receptionists</li>
                      <li>✓ 📞 <strong>Dedicated Twilio AI Call Bot</strong></li>
                      <li>✓ 💬 <strong>WhatsApp Intake & Reminders</strong></li>
                      <li>✓ 🖥️ Receptionist & Doctor Workstations</li>
                    </ul>
                  </div>

                  <button 
                    onClick={() => handleSelectPlanAndOnboard('PRO')}
                    style={{ width: '100%', padding: '13px', borderRadius: '12px', border: 'none', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', color: '#FFFFFF', fontWeight: 800, fontSize: '14px', cursor: 'pointer', marginTop: '24px', boxShadow: '0 4px 14px rgba(37,99,235,0.35)', transition: 'all 0.2s' }}
                  >
                    Choose Pro AI Plan →
                  </button>
                </div>

                {/* Enterprise Plan */}
                <div className="pricing-card-hover" style={{ background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '22px', padding: '30px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 8px 24px rgba(15,23,42,0.04)' }}>
                  <div>
                    <div style={{ fontSize: '18px', fontWeight: 800, color: '#7E22CE' }}>🥇 Enterprise Plan</div>
                    <div style={{ fontSize: '30px', fontWeight: 900, color: '#0F172A', margin: '12px 0 4px 0' }}>
                      ₹29,999 <span style={{ fontSize: '14px', color: '#64748B', fontWeight: 600 }}>/ year</span>
                    </div>
                    <p style={{ fontSize: '12px', color: '#64748B', marginBottom: '20px', fontWeight: 600 }}>For large multi-specialty hospitals needing custom branding.</p>

                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#334155', fontWeight: 600 }}>
                      <li>✓ 👨‍⚕️ <strong>Unlimited Doctors & Staff</strong></li>
                      <li>✓ ⚡ <strong>Priority AI Voice Line</strong></li>
                      <li>✓ 💬 Custom WhatsApp AI Bot</li>
                      <li>✓ 🎨 Custom Domain & Branding</li>
                    </ul>
                  </div>

                  <button 
                    onClick={() => handleSelectPlanAndOnboard('ENTERPRISE')}
                    style={{ width: '100%', padding: '13px', borderRadius: '12px', border: '1.5px solid #CBD5E1', background: '#F8FAFC', color: '#0F172A', fontWeight: 800, fontSize: '14px', cursor: 'pointer', marginTop: '24px', transition: 'all 0.2s' }}
                  >
                    Choose Enterprise Plan →
                  </button>
                </div>

              </div>
            </div>
          </section>

          {/* Interactive Features Section (BELOW PRICING) */}
          <section id="features" style={{ padding: '60px 20px 80px', background: '#FFFFFF', borderTop: '2px solid #DBEAFE' }}>
            <div style={{ maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
              <span style={{ color: '#2563EB', fontSize: '13px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                ENTERPRISE SaaS FEATURES
              </span>
              <h2 style={{ fontSize: '30px', fontWeight: 900, color: '#0F172A', margin: '6px 0 36px 0' }}>
                Everything Your Hospital Needs for 24/7 Automation
              </h2>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', textAlign: 'left' }}>
                {[
                  { icon: '📞', title: 'AI Voice Receptionist', desc: 'Handles incoming patient phone calls in Hindi & English and books appointments in real-time.' },
                  { icon: '🗓️', title: 'OPD Schedule Grid', desc: '4-Column session grid for doctors with double-booking prevention and leave tracking.' },
                  { icon: '💬', title: 'WhatsApp Automation', desc: 'Instant WhatsApp confirmation messages and prescription PDFs sent straight to patients.' },
                  { icon: '📊', title: 'Hospital Analytics', desc: 'Track daily OPD revenue, collection due, doctor workloads, and patient visit trends.' }
                ].map(f => (
                  <div key={f.title} style={{ background: '#F8FAFC', border: '1.5px solid #E2E8F0', borderRadius: '18px', padding: '24px', transition: 'transform 0.2s' }}>
                    <div style={{ fontSize: '36px', marginBottom: '14px' }}>{f.icon}</div>
                    <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>{f.title}</h3>
                    <p style={{ fontSize: '12px', color: '#64748B', lineHeight: 1.5, margin: 0, fontWeight: 600 }}>{f.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ── VIEW 2: 2-COLUMN SPLIT ANIMATED SIGN IN PAGE (`pageView === 'login'`) (MATCHING SCREENSHOT 1) ── */}
      {pageView === 'login' && (
        <section className="animate-fade-scale" style={{ padding: '50px 20px', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
          <button 
            onClick={() => setPageView('landing')}
            style={{ background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '10px', padding: '8px 16px', color: '#475569', cursor: 'pointer', fontSize: '13px', fontWeight: 800, marginBottom: '20px', boxShadow: '0 2px 8px rgba(15,23,42,0.05)' }}
          >
            ← Back to Home
          </button>

          {/* 2-Column Split Container (Matching Screenshot 1 Layout with Medical Blue Theme) */}
          <div style={{
            background: '#FFFFFF', borderRadius: '28px', border: '2px solid #DBEAFE',
            boxShadow: '0 20px 50px rgba(37,99,235,0.12)', display: 'grid', gridTemplateColumns: '1.1fr 0.9fr',
            overflow: 'hidden'
          }}>
            
            {/* LEFT COLUMN: UNIVERSAL SIGN IN FORM */}
            <div style={{ padding: '48px 40px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div style={{ marginBottom: '28px' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#EFF6FF', color: '#2563EB', padding: '4px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 800, marginBottom: '12px' }}>
                  <Shield size={14} /> Hospital Staff & Management Portal
                </div>
                <h2 style={{ fontSize: '28px', fontWeight: 900, color: '#0F172A', margin: 0, letterSpacing: '-0.5px' }}>
                  Sign In to Workstation
                </h2>
                <p style={{ fontSize: '14px', color: '#64748B', margin: '8px 0 0 0', fontWeight: 600, lineHeight: 1.5 }}>
                  Enter your credentials. You will be automatically routed to your assigned desk.
                </p>
              </div>

              {loginError && (
                <div style={{ color: '#DC2626', fontSize: '13px', fontWeight: 700, background: '#FEE2E2', padding: '12px 14px', borderRadius: '12px', marginBottom: '20px', border: '1.5px solid #FECACA' }}>
                  ⚠️ {loginError}
                </div>
              )}

              <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                <div className="form-group">
                  <label style={{ fontSize: '13px', color: '#0F172A', fontWeight: 700, marginBottom: '6px', display: 'block' }}>Username or Email</label>
                  <input 
                    type="text" className="form-control" 
                    value={loginUsername} onChange={e => setLoginUsername(e.target.value)} 
                    placeholder="Enter your username or email" required 
                    style={{ borderRadius: '12px', padding: '14px 16px', fontSize: '14px', border: '1.5px solid #CBD5E1', fontWeight: 600, color: '#0F172A', width: '100%' }} 
                  />
                </div>
                
                <div className="form-group">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label style={{ fontSize: '13px', color: '#0F172A', fontWeight: 700, margin: 0 }}>Password</label>
                  </div>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <input 
                      type={showLoginPassword ? 'text' : 'password'} 
                      className="form-control" 
                      value={loginPassword} onChange={e => setLoginPassword(e.target.value)} 
                      placeholder="••••••••" required 
                      style={{ width: '100%', borderRadius: '12px', padding: '14px 44px 14px 16px', fontSize: '14px', border: '1.5px solid #CBD5E1', fontWeight: 600, color: '#0F172A' }} 
                    />
                    <button 
                      type="button" 
                      onClick={() => setShowLoginPassword(!showLoginPassword)}
                      style={{ position: 'absolute', right: '14px', background: 'none', border: 'none', color: '#64748B', cursor: 'pointer', padding: '4px' }}
                    >
                      {showLoginPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <button type="submit" className="btn btn-primary" style={{ padding: '14px', borderRadius: '12px', fontSize: '15px', fontWeight: 800, marginTop: '8px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', boxShadow: '0 4px 16px rgba(37,99,235,0.35)', cursor: 'pointer' }}>
                  Sign In Securely →
                </button>
              </form>

              <div style={{ textAlign: 'center', marginTop: '24px', paddingTop: '20px', borderTop: '1px solid #F1F5F9', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span style={{ fontSize: '13px', color: '#64748B', fontWeight: 600 }}>Need a new hospital workspace?</span>
                <button 
                  type="button" 
                  onClick={() => setPageView('onboard')} 
                  style={{ background: 'none', border: 'none', color: '#2563EB', cursor: 'pointer', fontSize: '13px', fontWeight: 800, textDecoration: 'underline' }}
                >
                  🏥 Onboard Your Hospital & Choose Plan
                </button>
              </div>
            </div>

            {/* RIGHT COLUMN: VIBRANT MEDICAL AI ILLUSTRATION PANEL (MATCHING SCREENSHOT 1 RIGHT PANEL) */}
            <div style={{
              background: 'linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%)',
              padding: '44px 36px', color: '#FFFFFF', display: 'flex', flexDirection: 'column',
              justify: 'space-between', position: 'relative', overflow: 'hidden'
            }}>
              <div style={{ position: 'relative', zIndex: 2 }}>
                <div style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: '30px', padding: '6px 16px', fontSize: '12px', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '6px', marginBottom: '24px' }}>
                  ⚡ AURA SaaS Healthcare AI
                </div>

                <h3 style={{ fontSize: '26px', fontWeight: 900, lineHeight: 1.3, marginBottom: '14px' }}>
                  24/7 AI Voice Call Booking & OPD Management
                </h3>
                
                <p style={{ fontSize: '13px', color: '#DBEAFE', fontWeight: 600, lineHeight: 1.6, marginBottom: '28px' }}>
                  Automate patient intake, manage doctor schedules, send instant WhatsApp PDF prescriptions, and track hospital revenue in real-time.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {[
                    '24/7 AI Voice Call Handling in Hindi & English',
                    'Real-Time OPD Doctor Scheduling Grid',
                    'Instant WhatsApp Prescription PDFs',
                    'Multi-Tenant SaaS Data Isolation'
                  ].map(item => (
                    <div key={item} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', fontWeight: 700, background: 'rgba(255,255,255,0.1)', padding: '10px 14px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.15)' }}>
                      <CheckCircle2 size={16} color="#60A5FA" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 700, marginTop: '30px', zIndex: 2 }}>
                🔒 HIPAA & ISO 27001 Security Compliant
              </div>
            </div>

          </div>
        </section>
      )}

      {/* ── VIEW 3: DEDICATED ANIMATED HOSPITAL ONBOARDING PAGE (`pageView === 'onboard'`) ── */}
      {pageView === 'onboard' && (
        <section className="animate-fade-scale" style={{ padding: '50px 20px', maxWidth: '580px', margin: '0 auto', width: '100%' }}>
          <button 
            onClick={() => setPageView('landing')}
            style={{ background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '10px', padding: '8px 16px', color: '#475569', cursor: 'pointer', fontSize: '13px', fontWeight: 800, marginBottom: '20px', boxShadow: '0 2px 8px rgba(15,23,42,0.05)' }}
          >
            ← Back to Home
          </button>

          <div style={{ background: 'rgba(255,255,255,0.96)', backdropFilter: 'blur(16px)', borderRadius: '28px', border: '2.5px solid #BFDBFE', padding: '36px', boxShadow: '0 16px 48px rgba(37,99,235,0.12)' }}>
            
            <h2 style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '0 0 4px 0', textAlign: 'center' }}>
              🏥 Onboard Your Hospital Account
            </h2>
            <p style={{ fontSize: '13px', color: '#64748B', textAlign: 'center', margin: '0 0 20px 0', fontWeight: 600 }}>
              Complete registration details for your selected subscription plan.
            </p>

            {/* Selected Plan Summary Banner */}
            <div style={{
              background: selectedPlan === 'ENTERPRISE' ? '#F3E8FF' : selectedPlan === 'PRO' ? '#EFF6FF' : '#F8FAFC',
              border: `2px solid ${selectedPlan === 'ENTERPRISE' ? '#D8B4FE' : selectedPlan === 'PRO' ? '#BFDBFE' : '#CBD5E1'}`,
              borderRadius: '16px', padding: '14px 18px', marginBottom: '20px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ fontSize: '26px' }}>
                  {selectedPlan === 'ENTERPRISE' ? '🥇' : selectedPlan === 'PRO' ? '🥈' : '🥉'}
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 800, textTransform: 'uppercase' }}>Selected Subscription Plan</div>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>
                    {selectedPlan === 'ENTERPRISE' ? 'Enterprise Plan (₹29,999/yr)' : selectedPlan === 'PRO' ? 'Pro AI Plan (₹2,999/mo)' : 'Starter Trial Plan (15-Day Free)'}
                  </div>
                </div>
              </div>
              <button 
                type="button"
                onClick={() => scrollToSection('pricing')}
                style={{ background: 'none', border: 'none', color: '#2563EB', fontSize: '12px', fontWeight: 800, cursor: 'pointer', textDecoration: 'underline' }}
              >
                Change Plan
              </button>
            </div>

            {onboardError && (
              <div style={{ color: '#DC2626', fontSize: '13px', fontWeight: 700, background: '#FEE2E2', padding: '12px 14px', borderRadius: '10px', marginBottom: '16px', border: '1.5px solid #FECACA' }}>
                ⚠️ {onboardError}
              </div>
            )}

            <form onSubmit={handleOpenCheckout} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="form-group">
                <label style={{ fontSize: '12px', color: '#475569', fontWeight: 700, marginBottom: '4px', display: 'block' }}>Hospital Name *</label>
                <input type="text" className="form-control" value={hospName} onChange={e => setHospName(e.target.value)} placeholder="e.g. Apollo Multispeciality" required style={{ borderRadius: '10px', padding: '11px', fontSize: '13px' }} />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div className="form-group">
                  <label style={{ fontSize: '12px', color: '#475569', fontWeight: 700, marginBottom: '4px', display: 'block' }}>Hospital Contact Phone *</label>
                  <input type="text" className="form-control" value={hospPhone} onChange={e => setHospPhone(e.target.value)} placeholder="+919876543210" required style={{ borderRadius: '10px', padding: '11px', fontSize: '13px' }} />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '12px', color: '#475569', fontWeight: 700, marginBottom: '4px', display: 'block' }}>City / Address</label>
                  <input type="text" className="form-control" value={hospAddress} onChange={e => setHospAddress(e.target.value)} placeholder="City, State" style={{ borderRadius: '10px', padding: '11px', fontSize: '13px' }} />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '12px', color: '#475569', fontWeight: 700, marginBottom: '4px', display: 'block' }}>Admin Username *</label>
                  <input type="text" className="form-control" value={hospAdminUsername} onChange={e => setHospAdminUsername(e.target.value)} placeholder="admin_username" required style={{ borderRadius: '10px', padding: '11px', fontSize: '13px' }} />
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '12px', color: '#475569', fontWeight: 700, marginBottom: '4px', display: 'block' }}>Admin Email *</label>
                  <input type="email" className="form-control" value={hospAdminEmail} onChange={e => setHospAdminEmail(e.target.value)} placeholder="admin@hospital.com" required style={{ borderRadius: '10px', padding: '11px', fontSize: '13px' }} />
                </div>
              </div>

              <div className="form-group">
                <label style={{ fontSize: '12px', color: '#475569', fontWeight: 700, marginBottom: '4px', display: 'block' }}>Admin Password *</label>
                <input type="password" className="form-control" value={hospAdminPassword} onChange={e => setHospAdminPassword(e.target.value)} placeholder="••••••••" required style={{ borderRadius: '10px', padding: '11px', fontSize: '13px' }} />
              </div>

              <button type="submit" className="btn btn-primary" style={{ padding: '14px', borderRadius: '12px', fontSize: '15px', fontWeight: 800, marginTop: '8px' }}>
                Proceed to Payment & Activation →
              </button>
            </form>
          </div>
        </section>
      )}

      {/* ── FOOTER ── */}
      <footer style={{ background: '#0F172A', color: '#94A3B8', padding: '24px 40px', textAlign: 'center', fontSize: '13px', borderTop: '1px solid #1E293B', marginTop: 'auto' }}>
        <div>© 2026 AURA SaaS AI Hospital Management Platform. All rights reserved.</div>
      </footer>

    </div>
  );
}
