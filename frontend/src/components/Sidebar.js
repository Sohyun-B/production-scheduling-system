import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { 
  Home, 
  Calendar, 
  BarChart3, 
  Settings, 
  ChevronRight,
  Database,
  Cpu,
  FileText,
  Layers
} from 'lucide-react';

const SidebarContainer = styled.aside`
  position: fixed;
  top: 0;
  left: 0;
  width: 250px;
  height: 100vh;
  background: white;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  
  @media (max-width: 768px) {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    
    &.open {
      transform: translateX(0);
    }
  }
`;

const SidebarHeader = styled.div`
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
`;

const SidebarTitle = styled.h2`
  font-size: 1.125rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
`;

const SidebarContent = styled.nav`
  flex: 1;
  padding: 1rem 0;
`;

const MenuSection = styled.div`
  margin-bottom: 2rem;
`;

const SectionTitle = styled.h3`
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 0.5rem 1.5rem;
`;

const MenuItem = styled.button`
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1.5rem;
  border: none;
  background: ${props => props.active ? '#f1f5f9' : 'transparent'};
  color: ${props => props.active ? '#1e293b' : '#64748b'};
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  font-weight: ${props => props.active ? '600' : '400'};

  &:hover {
    background: #f8fafc;
    color: #1e293b;
  }

  &:active {
    transform: scale(0.98);
  }
`;

const MenuIcon = styled.span`
  margin-right: 0.75rem;
  display: flex;
  align-items: center;
`;

const MenuText = styled.span`
  flex: 1;
`;

const MenuArrow = styled.span`
  opacity: ${props => props.active ? 1 : 0};
  transition: opacity 0.2s ease;
`;

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    {
      section: 'Main',
      items: [
        { path: '/', icon: Home, label: '대시보드' },
        { path: '/scheduling', icon: Calendar, label: '스케줄링' },
        { path: '/step-by-step', icon: Layers, label: '단계별 스케줄링' },
        { path: '/results', icon: BarChart3, label: '결과 분석' },
      ]
    },
    {
      section: 'System',
      items: [
        { path: '/settings', icon: Settings, label: '설정' },
      ]
    }
  ];

  const handleMenuClick = (path) => {
    navigate(path);
  };

  return (
    <SidebarContainer>
      <SidebarHeader>
        <SidebarTitle>Production Scheduling</SidebarTitle>
      </SidebarHeader>
      
      <SidebarContent>
        {menuItems.map((section) => (
          <MenuSection key={section.section}>
            <SectionTitle>{section.section}</SectionTitle>
            {section.items.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              
              return (
                <MenuItem
                  key={item.path}
                  active={isActive}
                  onClick={() => handleMenuClick(item.path)}
                >
                  <MenuIcon>
                    <Icon size={18} />
                  </MenuIcon>
                  <MenuText>{item.label}</MenuText>
                  <MenuArrow active={isActive}>
                    <ChevronRight size={16} />
                  </MenuArrow>
                </MenuItem>
              );
            })}
          </MenuSection>
        ))}
      </SidebarContent>
    </SidebarContainer>
  );
};

export default Sidebar;
