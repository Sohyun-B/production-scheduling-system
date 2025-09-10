import React, { useState } from 'react';
import styled from 'styled-components';
import { Upload, FileText, Database, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

const FormContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
`;

const FormTitle = styled.h2`
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1.5rem;
`;

const UploadOptions = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 2rem;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const UploadOption = styled.div`
  border: 2px dashed #e2e8f0;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: ${props => props.active ? '#f0f9ff' : 'white'};
  border-color: ${props => props.active ? '#3b82f6' : '#e2e8f0'};

  &:hover {
    border-color: #3b82f6;
    background: #f0f9ff;
  }
`;

const OptionIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #f1f5f9;
  margin: 0 auto 1rem;
  color: #64748b;
`;

const OptionTitle = styled.h3`
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
`;

const OptionDescription = styled.p`
  font-size: 0.875rem;
  color: #64748b;
  margin: 0;
`;

const FileInput = styled.input`
  display: none;
`;

const ExternalApiForm = styled.div`
  background: #f8fafc;
  border-radius: 8px;
  padding: 1.5rem;
  margin-top: 1rem;
`;

const FormGroup = styled.div`
  margin-bottom: 1rem;
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

const SubmitButton = styled.button`
  width: 100%;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;

  &:hover:not(:disabled) {
    background: #2563eb;
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const DataUploadForm = ({ onDataUpload, disabled }) => {
  const [uploadType, setUploadType] = useState('file');
  const [apiConfig, setApiConfig] = useState({
    base_url: 'http://localhost:8000',
    api_key: '',
    use_mock: true
  });

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.type !== 'application/json') {
      toast.error('JSON 파일만 업로드할 수 있습니다.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        onDataUpload(data);
        toast.success('데이터가 성공적으로 업로드되었습니다.');
      } catch (error) {
        toast.error('JSON 파일을 읽을 수 없습니다.');
      }
    };
    reader.readAsText(file);
  };

  const handleExternalApiSubmit = () => {
    if (!apiConfig.base_url) {
      toast.error('API URL을 입력해주세요.');
      return;
    }

    onDataUpload({ apiConfig });
    toast.success('외부 API에서 데이터를 로딩합니다.');
  };

  return (
    <FormContainer>
      <FormTitle>데이터 업로드</FormTitle>
      
      <UploadOptions>
        <UploadOption
          active={uploadType === 'file'}
          onClick={() => setUploadType('file')}
        >
          <OptionIcon>
            <FileText size={24} />
          </OptionIcon>
          <OptionTitle>파일 업로드</OptionTitle>
          <OptionDescription>
            JSON 파일을 업로드하여 데이터를 로딩합니다.
          </OptionDescription>
          <FileInput
            type="file"
            accept=".json"
            onChange={handleFileUpload}
            disabled={disabled}
          />
        </UploadOption>

        <UploadOption
          active={uploadType === 'api'}
          onClick={() => setUploadType('api')}
        >
          <OptionIcon>
            <ExternalLink size={24} />
          </OptionIcon>
          <OptionTitle>외부 API</OptionTitle>
          <OptionDescription>
            외부 API에서 데이터를 직접 로딩합니다.
          </OptionDescription>
        </UploadOption>
      </UploadOptions>

      {uploadType === 'api' && (
        <ExternalApiForm>
          <FormGroup>
            <Label>API URL</Label>
            <Input
              type="url"
              value={apiConfig.base_url}
              onChange={(e) => setApiConfig({ ...apiConfig, base_url: e.target.value })}
              placeholder="https://api.example.com"
            />
          </FormGroup>
          
          <FormGroup>
            <Label>API Key (선택사항)</Label>
            <Input
              type="text"
              value={apiConfig.api_key}
              onChange={(e) => setApiConfig({ ...apiConfig, api_key: e.target.value })}
              placeholder="your-api-key"
            />
          </FormGroup>
          
          <FormGroup>
            <CheckboxContainer>
              <Checkbox
                type="checkbox"
                id="use_mock"
                checked={apiConfig.use_mock}
                onChange={(e) => setApiConfig({ ...apiConfig, use_mock: e.target.checked })}
              />
              <CheckboxLabel htmlFor="use_mock">
                Mock API 사용 (테스트용)
              </CheckboxLabel>
            </CheckboxContainer>
          </FormGroup>
          
          <SubmitButton
            onClick={handleExternalApiSubmit}
            disabled={disabled}
          >
            <Database size={18} />
            외부 API에서 데이터 로딩
          </SubmitButton>
        </ExternalApiForm>
      )}

      {uploadType === 'file' && (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <Upload size={48} color="#64748b" />
          <p style={{ marginTop: '1rem', color: '#64748b' }}>
            JSON 파일을 선택하거나 클릭하여 업로드하세요.
          </p>
        </div>
      )}
    </FormContainer>
  );
};

export default DataUploadForm;
