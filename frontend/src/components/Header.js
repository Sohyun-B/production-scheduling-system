import React from 'react';
import styled from 'styled-components';
import { Calendar, Bell, Settings, User } from 'lucide-react';

const HeaderContainer = styled.header`
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  
  @media (max-width: 768px) {
    padding: 1rem;
  }
`;

const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
`;

const HeaderActions = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const ActionButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: #f1f5f9;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: #e2e8f0;
    color: #475569;
  }

  &:active {
    transform: scale(0.95);
  }
`;

const NotificationBadge = styled.span`
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
`;

const UserInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #64748b;
`;

const Header = () => {
  return (
    <HeaderContainer>
      <Logo>
        <Calendar size={24} />
        Production Scheduling
      </Logo>
      
      <HeaderActions>
        <div style={{ position: 'relative' }}>
          <ActionButton>
            <Bell size={20} />
          </ActionButton>
          <NotificationBadge />
        </div>
        
        <ActionButton>
          <Settings size={20} />
        </ActionButton>
        
        <UserInfo>
          <User size={16} />
          <span>관리자</span>
        </UserInfo>
      </HeaderActions>
    </HeaderContainer>
  );
};

export default Header;
