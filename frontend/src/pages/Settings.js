import React, { useState } from 'react';
import styled from 'styled-components';
import { Save, RotateCcw, Database, Server, Bell } from 'lucide-react';
import toast from 'react-hot-toast';

const SettingsContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;
`;

const PageTitle = styled.h1`
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
`;

const PageDescription = styled.p`
  color: #64748b;
  font-size: 1rem;
`;

const SettingsGrid = styled.div`
  display: grid;
  gap: 2rem;
`;

const SettingsSection = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const SectionHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
`;

const SectionIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #f1f5f9;
  color: #64748b;
`;

const SectionTitle = styled.h2`
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
`;

const FormGroup = styled.div`
  margin-bottom: 1.5rem;
`;

const Label = styled.label`
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
`;

const Input = styled.input`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  transition: border-color 0.2s ease;

  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  background: white;
  transition: border-color 0.2s ease;

  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const CheckboxContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const Checkbox = styled.input`
  width: 16px;
  height: 16px;
`;

const CheckboxLabel = styled.label`
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  min-height: 100px;
  resize: vertical;
  transition: border-color 0.2s ease;

  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
`;

const Button = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
`;

const PrimaryButton = styled(Button)`
  background: #3b82f6;
  color: white;

  &:hover {
    background: #2563eb;
    transform: translateY(-1px);
  }
`;

const SecondaryButton = styled(Button)`
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;

  &:hover {
    background: #e2e8f0;
    color: #475569;
  }
`;

const Settings = () => {
  const [settings, setSettings] = useState({
    // API 설정
    pythonApiUrl: 'http://localhost:8000',
    nodeApiUrl: 'http://localhost:3001',
    timeout: 300,
    
    // 스케줄링 설정
    defaultWindowDays: 5,
    maxRetries: 3,
    autoSave: true,
    
    // 알림 설정
    emailNotifications: false,
    emailAddress: '',
    slackNotifications: false,
    slackWebhook: '',
    
    // 시스템 설정
    logLevel: 'info',
    debugMode: false,
    autoRefresh: true,
    refreshInterval: 30
  });

  const handleInputChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = () => {
    // 설정 저장 로직
    console.log('설정 저장:', settings);
    toast.success('설정이 저장되었습니다.');
  };

  const handleReset = () => {
    // 설정 초기화 로직
    setSettings({
      pythonApiUrl: 'http://localhost:8000',
      nodeApiUrl: 'http://localhost:3001',
      timeout: 300,
      defaultWindowDays: 5,
      maxRetries: 3,
      autoSave: true,
      emailNotifications: false,
      emailAddress: '',
      slackNotifications: false,
      slackWebhook: '',
      logLevel: 'info',
      debugMode: false,
      autoRefresh: true,
      refreshInterval: 30
    });
    toast.info('설정이 초기화되었습니다.');
  };

  return (
    <SettingsContainer>
      <PageHeader>
        <PageTitle>설정</PageTitle>
        <PageDescription>
          시스템 설정을 관리하고 환경을 구성하세요.
        </PageDescription>
      </PageHeader>

      <SettingsGrid>
        {/* API 설정 */}
        <SettingsSection>
          <SectionHeader>
            <SectionIcon>
              <Server size={20} />
            </SectionIcon>
            <SectionTitle>API 설정</SectionTitle>
          </SectionHeader>
          
          <FormGroup>
            <Label>Python API URL</Label>
            <Input
              type="url"
              value={settings.pythonApiUrl}
              onChange={(e) => handleInputChange('pythonApiUrl', e.target.value)}
              placeholder="http://localhost:8000"
            />
          </FormGroup>
          
          <FormGroup>
            <Label>Node.js API URL</Label>
            <Input
              type="url"
              value={settings.nodeApiUrl}
              onChange={(e) => handleInputChange('nodeApiUrl', e.target.value)}
              placeholder="http://localhost:3001"
            />
          </FormGroup>
          
          <FormGroup>
            <Label>요청 타임아웃 (초)</Label>
            <Input
              type="number"
              value={settings.timeout}
              onChange={(e) => handleInputChange('timeout', parseInt(e.target.value))}
              min="30"
              max="600"
            />
          </FormGroup>
        </SettingsSection>

        {/* 스케줄링 설정 */}
        <SettingsSection>
          <SectionHeader>
            <SectionIcon>
              <Database size={20} />
            </SectionIcon>
            <SectionTitle>스케줄링 설정</SectionTitle>
          </SectionHeader>
          
          <FormGroup>
            <Label>기본 윈도우 일수</Label>
            <Input
              type="number"
              value={settings.defaultWindowDays}
              onChange={(e) => handleInputChange('defaultWindowDays', parseInt(e.target.value))}
              min="1"
              max="30"
            />
          </FormGroup>
          
          <FormGroup>
            <Label>최대 재시도 횟수</Label>
            <Input
              type="number"
              value={settings.maxRetries}
              onChange={(e) => handleInputChange('maxRetries', parseInt(e.target.value))}
              min="0"
              max="10"
            />
          </FormGroup>
          
          <FormGroup>
            <CheckboxContainer>
              <Checkbox
                type="checkbox"
                id="autoSave"
                checked={settings.autoSave}
                onChange={(e) => handleInputChange('autoSave', e.target.checked)}
              />
              <CheckboxLabel htmlFor="autoSave">
                자동 저장 활성화
              </CheckboxLabel>
            </CheckboxContainer>
          </FormGroup>
        </SettingsSection>

        {/* 알림 설정 */}
        <SettingsSection>
          <SectionHeader>
            <SectionIcon>
              <Bell size={20} />
            </SectionIcon>
            <SectionTitle>알림 설정</SectionTitle>
          </SectionHeader>
          
          <FormGroup>
            <CheckboxContainer>
              <Checkbox
                type="checkbox"
                id="emailNotifications"
                checked={settings.emailNotifications}
                onChange={(e) => handleInputChange('emailNotifications', e.target.checked)}
              />
              <CheckboxLabel htmlFor="emailNotifications">
                이메일 알림 활성화
              </CheckboxLabel>
            </CheckboxContainer>
          </FormGroup>
          
          {settings.emailNotifications && (
            <FormGroup>
              <Label>이메일 주소</Label>
              <Input
                type="email"
                value={settings.emailAddress}
                onChange={(e) => handleInputChange('emailAddress', e.target.value)}
                placeholder="admin@company.com"
              />
            </FormGroup>
          )}
          
          <FormGroup>
            <CheckboxContainer>
              <Checkbox
                type="checkbox"
                id="slackNotifications"
                checked={settings.slackNotifications}
                onChange={(e) => handleInputChange('slackNotifications', e.target.checked)}
              />
              <CheckboxLabel htmlFor="slackNotifications">
                Slack 알림 활성화
              </CheckboxLabel>
            </CheckboxContainer>
          </FormGroup>
          
          {settings.slackNotifications && (
            <FormGroup>
              <Label>Slack Webhook URL</Label>
              <Input
                type="url"
                value={settings.slackWebhook}
                onChange={(e) => handleInputChange('slackWebhook', e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
              />
            </FormGroup>
          )}
        </SettingsSection>

        {/* 시스템 설정 */}
        <SettingsSection>
          <SectionHeader>
            <SectionIcon>
              <RotateCcw size={20} />
            </SectionIcon>
            <SectionTitle>시스템 설정</SectionTitle>
          </SectionHeader>
          
          <FormGroup>
            <Label>로그 레벨</Label>
            <Select
              value={settings.logLevel}
              onChange={(e) => handleInputChange('logLevel', e.target.value)}
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warn">Warning</option>
              <option value="error">Error</option>
            </Select>
          </FormGroup>
          
          <FormGroup>
            <CheckboxContainer>
              <Checkbox
                type="checkbox"
                id="debugMode"
                checked={settings.debugMode}
                onChange={(e) => handleInputChange('debugMode', e.target.checked)}
              />
              <CheckboxLabel htmlFor="debugMode">
                디버그 모드 활성화
              </CheckboxLabel>
            </CheckboxContainer>
          </FormGroup>
          
          <FormGroup>
            <CheckboxContainer>
              <Checkbox
                type="checkbox"
                id="autoRefresh"
                checked={settings.autoRefresh}
                onChange={(e) => handleInputChange('autoRefresh', e.target.checked)}
              />
              <CheckboxLabel htmlFor="autoRefresh">
                자동 새로고침 활성화
              </CheckboxLabel>
            </CheckboxContainer>
          </FormGroup>
          
          {settings.autoRefresh && (
            <FormGroup>
              <Label>새로고침 간격 (초)</Label>
              <Input
                type="number"
                value={settings.refreshInterval}
                onChange={(e) => handleInputChange('refreshInterval', parseInt(e.target.value))}
                min="5"
                max="300"
              />
            </FormGroup>
          )}
        </SettingsSection>
      </SettingsGrid>

      <ButtonGroup>
        <SecondaryButton onClick={handleReset}>
          <RotateCcw size={16} />
          초기화
        </SecondaryButton>
        <PrimaryButton onClick={handleSave}>
          <Save size={16} />
          저장
        </PrimaryButton>
      </ButtonGroup>
    </SettingsContainer>
  );
};

export default Settings;
