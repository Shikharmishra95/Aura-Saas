import React from 'react';
import { Calendar, UserPlus, Heart, Sliders, Shield } from 'lucide-react';

export default function Sidebar({
  token,
  userRole,
  activeTab,
  setActiveTab,
  t
}) {
  if (!token) return null;

  return (
    <aside style={{
      width: '240px',
      flexShrink: 0,
      background: '#FFFFFF',
      borderRight: '1.5px solid #DBEAFE',
      padding: '24px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px'
    }}>
      <div style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', padding: '0 8px' }}>
        Main Menu
      </div>

      {/* RECEPTIONIST TABS */}
      {userRole === 'RECEPTIONIST' && (
        <>
          <button 
            onClick={() => setActiveTab('overview')} 
            className={`sidebar-btn ${activeTab === 'overview' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'overview' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'overview' ? '#FFFFFF' : '#334155'
            }}
          >
            <Calendar size={18} /> Overview
          </button>

          <button 
            onClick={() => setActiveTab('new_booking')} 
            className={`sidebar-btn ${activeTab === 'new_booking' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'new_booking' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'new_booking' ? '#FFFFFF' : '#334155'
            }}
          >
            <UserPlus size={18} /> New Booking
          </button>

          <button 
            onClick={() => setActiveTab('receptionist_leaves')} 
            className={`sidebar-btn ${activeTab === 'receptionist_leaves' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'receptionist_leaves' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'receptionist_leaves' ? '#FFFFFF' : '#334155'
            }}
          >
            <Calendar size={18} /> Doctor Leaves
          </button>
        </>
      )}

      {/* DOCTOR TABS */}
      {userRole === 'DOCTOR' && (
        <button 
          onClick={() => setActiveTab('appointments')} 
          className={`sidebar-btn ${activeTab === 'appointments' ? 'active' : ''}`}
          style={{
            display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
            borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
            background: activeTab === 'appointments' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
            color: activeTab === 'appointments' ? '#FFFFFF' : '#334155'
          }}
        >
          <Heart size={18} /> My Appointments Queue
        </button>
      )}

      {/* HOSPITAL ADMIN TABS */}
      {userRole === 'ADMIN' && (
        <>
          <button 
            onClick={() => setActiveTab('admin_overview')} 
            className={`sidebar-btn ${activeTab === 'admin_overview' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'admin_overview' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'admin_overview' ? '#FFFFFF' : '#334155'
            }}
          >
            <Sliders size={18} /> Admin Overview
          </button>

          <button 
            onClick={() => setActiveTab('staff_management')} 
            className={`sidebar-btn ${activeTab === 'staff_management' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'staff_management' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'staff_management' ? '#FFFFFF' : '#334155'
            }}
          >
            <UserPlus size={18} /> Staff Management
          </button>

          <button 
            onClick={() => setActiveTab('hospital_overview')} 
            className={`sidebar-btn ${activeTab === 'hospital_overview' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'hospital_overview' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'hospital_overview' ? '#FFFFFF' : '#334155'
            }}
          >
            <Calendar size={18} /> Hospital Metrics
          </button>

          <button 
            onClick={() => setActiveTab('admin_leaves')} 
            className={`sidebar-btn ${activeTab === 'admin_leaves' ? 'active' : ''}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
              borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
              background: activeTab === 'admin_leaves' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
              color: activeTab === 'admin_leaves' ? '#FFFFFF' : '#334155'
            }}
          >
            <Calendar size={18} /> Leaves Approvals
          </button>
        </>
      )}

      {/* SUPER ADMIN TABS */}
      {userRole === 'SUPER_ADMIN' && (
        <button 
          onClick={() => setActiveTab('super_admin')} 
          className={`sidebar-btn ${activeTab === 'super_admin' ? 'active' : ''}`}
          style={{
            display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
            borderRadius: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', border: 'none',
            background: activeTab === 'super_admin' ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' : 'transparent',
            color: activeTab === 'super_admin' ? '#FFFFFF' : '#334155'
          }}
        >
          <Shield size={18} /> Platform Control Panel
        </button>
      )}
    </aside>
  );
}
