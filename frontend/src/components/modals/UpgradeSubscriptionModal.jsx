import React from 'react';

export default function UpgradeSubscriptionModal({
  isOpen,
  onClose,
  activeHospital,
  hospitalStats,
  plansList = [],
  hospitalId,
  onRenewPlan,
  onUpgradePlan,
  lang = 'en'
}) {
  if (!isOpen) return null;

  const currentActivePlan = activeHospital?.subscription_plan || hospitalStats?.subscription_plan || 'PRO';
  const isEnterprise = currentActivePlan === 'ENTERPRISE';
  const isStarter = currentActivePlan === 'STARTER';
  const isPro = currentActivePlan === 'PRO';

  const starterPlan = plansList.find((p) => p.plan_code === 'STARTER');
  const proPlan = plansList.find((p) => p.plan_code === 'PRO');
  const enterprisePlan = plansList.find((p) => p.plan_code === 'ENTERPRISE');

  const starterPrice = starterPlan ? Number(starterPlan.price_inr) : 1500;
  const proPrice = proPlan ? Number(proPlan.price_inr) : 2999;
  const enterprisePrice = enterprisePlan ? Number(enterprisePlan.price_inr) : 29999;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1100,
        padding: '20px'
      }}
    >
      <div
        className="animate-modal-pop"
        style={{
          background: '#FFFFFF',
          borderRadius: '24px',
          width: '100%',
          maxWidth: '780px',
          padding: '32px',
          boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.3)',
          border: '1.5px solid #DBEAFE',
          textAlign: 'left'
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid #F1F5F9',
            paddingBottom: '16px',
            marginBottom: '16px'
          }}
        >
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
              ⚡ {lang === 'hi' ? 'सब्सक्रिप्शन एवं प्लान प्रबंधन' : 'Subscription & Plan Management'}
            </h3>
            <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 600, marginTop: '2px' }}>
              {lang === 'hi' ? 'वर्तमान सक्रिय प्लान:' : 'Current Active Plan:'}{' '}
              <strong style={{ color: isEnterprise ? '#7E22CE' : isPro ? '#2563EB' : '#D97706' }}>
                {isEnterprise ? '👑 ENTERPRISE 360' : isPro ? '⚡ PRO AI PLAN' : '⭐ STARTER (15-Day Trial)'}
              </strong>{' '}
              •{' '}
              {activeHospital?.days_left !== undefined
                ? `${activeHospital.days_left} ${lang === 'hi' ? 'दिन शेष' : 'Days Left'}`
                : ''}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#F1F5F9',
              border: 'none',
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              fontSize: '16px',
              cursor: 'pointer',
              color: '#64748B',
              fontWeight: 800
            }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            background: activeHospital?.is_expired
              ? '#FEF2F2'
              : activeHospital?.days_left <= 7
              ? '#FFFBEB'
              : '#F0FDF4',
            border: `1.5px solid ${
              activeHospital?.is_expired
                ? '#FECACA'
                : activeHospital?.days_left <= 7
                ? '#FDE68A'
                : '#BBF7D0'
            }`,
            borderRadius: '12px',
            padding: '12px 16px',
            marginBottom: '20px',
            color: activeHospital?.is_expired
              ? '#991B1B'
              : activeHospital?.days_left <= 7
              ? '#92400E'
              : '#166534',
            fontSize: '12px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span>{activeHospital?.is_expired ? '🚨' : activeHospital?.days_left <= 7 ? '⚠️' : '✓'}</span>
          <span>
            {activeHospital?.is_expired
              ? lang === 'hi'
                ? 'आपका प्लान समाप्त हो चुका है। सेवाओं को तुरंत सक्रिय करने के लिए नीचे दिए गए प्लान का चयन करें।'
                : 'Your subscription has expired. Please select a plan below to reactivate all services.'
              : lang === 'hi'
              ? 'प्लान समाप्ति से पहले रिन्यू या अपग्रेड करें ताकि AI रिसेप्शनिस्ट और व्हाट्सएप सेवाएं बिना रुकावट चलती रहें।'
              : 'Renew or upgrade before expiration to maintain uninterrupted 24/7 AI Voice reception and doctor operations.'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isStarter ? 'repeat(auto-fit, minmax(220px, 1fr))' : isEnterprise ? '1fr' : '1fr 1fr',
            gap: '16px',
            marginBottom: '20px'
          }}
        >
          {/* Option 1: Starter Renewal (Only shown for Starter Hospitals) */}
          {isStarter && (
            <div
              style={{
                background: '#F8FAFC',
                border: '2px solid #CBD5E1',
                borderRadius: '18px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 4px 14px rgba(15, 23, 42, 0.04)'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '14px', fontWeight: 800, color: '#334155' }}>
                    🥉 {lang === 'hi' ? 'स्टार्टर रिन्यूअल' : 'Starter Renewal'}
                  </span>
                  <span
                    style={{
                      background: '#F1F5F9',
                      color: '#475569',
                      padding: '2px 8px',
                      borderRadius: '6px',
                      fontSize: '10px',
                      fontWeight: 800
                    }}
                  >
                    +30 Days
                  </span>
                </div>
                <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '8px 0 4px 0' }}>
                  ₹{starterPrice.toLocaleString()}{' '}
                  <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>/ month</span>
                </div>
                <ul
                  style={{
                    listStyle: 'none',
                    padding: 0,
                    margin: '10px 0 16px 0',
                    fontSize: '11px',
                    color: '#475569',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    fontWeight: 600
                  }}
                >
                  <li>
                    ✓ 👨‍⚕️ <strong>{starterPlan?.max_doctors || 1} {lang === 'hi' ? 'डॉक्टर प्रोफाइल' : 'Doctor Profile'}</strong>
                  </li>
                  <li>✓ 🖥️ {lang === 'hi' ? 'रिसेप्शनिस्ट वर्कस्पेस' : 'Receptionist Portal'}</li>
                  <li>✓ 📱 {lang === 'hi' ? 'ऑनलाइन बुकिंग' : 'Online Booking'}</li>
                  <li>
                    ❌ 🔒 <strong>{lang === 'hi' ? 'AI वॉइस हेल्पलाइन बंद' : 'AI Voice Helpline Locked'}</strong>
                  </li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => onRenewPlan(hospitalId)}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: '1.5px solid #CBD5E1',
                  background: '#FFFFFF',
                  color: '#0F172A',
                  fontWeight: 800,
                  fontSize: '13px',
                  cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(15,23,42,0.05)'
                }}
              >
                {lang === 'hi'
                  ? `स्टार्टर रिन्यू करें (₹${starterPrice.toLocaleString()})`
                  : `Renew Starter (₹${starterPrice.toLocaleString()}) →`}
              </button>
            </div>
          )}

          {/* Option 2: Pro AI Plan (Upgrade or Renew) */}
          <div
            style={{
              background: '#F0FDF4',
              border: '2.5px solid #2563EB',
              borderRadius: '18px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 8px 24px rgba(37, 99, 235, 0.12)',
              position: 'relative'
            }}
          >
            {isStarter && (
              <span
                style={{
                  position: 'absolute',
                  top: '-12px',
                  right: '16px',
                  background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                  color: '#FFFFFF',
                  fontSize: '10px',
                  fontWeight: 800,
                  padding: '3px 10px',
                  borderRadius: '12px'
                }}
              >
                RECOMMENDED
              </span>
            )}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '14px', fontWeight: 800, color: '#2563EB' }}>
                  {isStarter
                    ? '⚡ PRO AI PLAN'
                    : isEnterprise
                    ? '🔄 Renew Enterprise'
                    : '🔄 Renew PRO Plan'}
                </span>
                <span
                  style={{
                    background: '#DBEAFE',
                    color: '#1E40AF',
                    padding: '2px 8px',
                    borderRadius: '6px',
                    fontSize: '10px',
                    fontWeight: 800
                  }}
                >
                  +{isEnterprise ? '365' : '30'} Days
                </span>
              </div>
              <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '8px 0 4px 0' }}>
                ₹{isEnterprise ? enterprisePrice.toLocaleString() : proPrice.toLocaleString()}{' '}
                <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>
                  {isEnterprise ? '/ year' : '/ month'}
                </span>
              </div>
              <ul
                style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: '10px 0 16px 0',
                  fontSize: '11px',
                  color: '#334155',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  fontWeight: 600
                }}
              >
                <li>
                  ✓ 📞 <strong>{lang === 'hi' ? '24/7 AI वॉइस रिसेप्शनिस्ट' : '24/7 AI Voice Receptionist'}</strong>
                </li>
                <li>
                  ✓ 👨‍⚕️ <strong>{isEnterprise ? 'Unlimited' : proPlan?.max_doctors || '5'} {lang === 'hi' ? 'डॉक्टर क्षमता' : 'Doctors Capacity'}</strong>
                </li>
                <li>✓ 💬 <strong>{lang === 'hi' ? 'व्हाट्सएप ऑटोमेशन' : 'WhatsApp Automation'}</strong></li>
                <li>✓ 💳 <strong>{lang === 'hi' ? 'ऑनलाइन OPD पेमेंट' : 'Online OPD Payments'}</strong></li>
              </ul>
            </div>
            <button
              type="button"
              onClick={() => {
                if (isStarter) {
                  onUpgradePlan(hospitalId, 'PRO');
                } else {
                  onRenewPlan(hospitalId);
                }
              }}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '10px',
                border: 'none',
                background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                color: '#FFFFFF',
                fontWeight: 800,
                fontSize: '13px',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(37,99,235,0.3)'
              }}
            >
              {isStarter
                ? `Upgrade to Pro (₹${proPrice.toLocaleString()}) →`
                : `Pay & Renew (₹${isEnterprise ? enterprisePrice.toLocaleString() : proPrice.toLocaleString()}) →`}
            </button>
          </div>

          {/* Option 3: Upgrade to Enterprise 360 */}
          {!isEnterprise && (
            <div
              style={{
                background: '#FAF5FF',
                border: '2px solid #7E22CE',
                borderRadius: '18px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 4px 14px rgba(126, 34, 206, 0.08)'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '14px', fontWeight: 800, color: '#7E22CE' }}>👑 ENTERPRISE 360</span>
                  <span
                    style={{
                      background: '#F3E8FF',
                      color: '#6B21A8',
                      padding: '2px 8px',
                      borderRadius: '6px',
                      fontSize: '10px',
                      fontWeight: 800
                    }}
                  >
                    +365 Days
                  </span>
                </div>
                <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '8px 0 4px 0' }}>
                  ₹{enterprisePrice.toLocaleString()}{' '}
                  <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>/ year</span>
                </div>
                <ul
                  style={{
                    listStyle: 'none',
                    padding: 0,
                    margin: '10px 0 16px 0',
                    fontSize: '11px',
                    color: '#334155',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    fontWeight: 600
                  }}
                >
                  <li>
                    ✓ 👨‍⚕️ <strong>{lang === 'hi' ? 'असीमित डॉक्टर्स (Unlimited)' : 'Unlimited Doctors'}</strong>
                  </li>
                  <li>✓ ⚡ <strong>{lang === 'hi' ? 'प्राथमिकता AI वॉइस रूटिंग' : 'Priority AI Voice Routing'}</strong></li>
                  <li>✓ 🎨 <strong>{lang === 'hi' ? 'कस्टम डोमेन एवं ब्रांडिंग' : 'Custom Domain & Branding'}</strong></li>
                  <li>✓ 🛡️ <strong>{lang === 'hi' ? '99.99% SRE अपटाइम गारंटी' : '99.99% SRE Uptime SLA'}</strong></li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => onUpgradePlan(hospitalId, 'ENTERPRISE')}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #7E22CE 0%, #6B21A8 100%)',
                  color: '#FFFFFF',
                  fontWeight: 800,
                  fontSize: '13px',
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(126,34,206,0.25)'
                }}
              >
                Upgrade Enterprise (₹{enterprisePrice.toLocaleString()}) →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
