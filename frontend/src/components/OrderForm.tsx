import React, { useState, useEffect } from 'react';
import { Order } from '../services/api';
import './OrderForm.css';

interface OrderFormProps {
  order?: Order | null;
  onSubmit: (orderData: Omit<Order, 'id' | 'created_at' | 'updated_at'>) => void;
  onCancel: () => void;
}

const OrderForm: React.FC<OrderFormProps> = ({ order, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    po_no: '',
    gitem: '',
    gitem_name: '',
    width: 0,
    length: 0,
    request_amount: 0,
    due_date: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (order) {
      setFormData({
        po_no: order.po_no,
        gitem: order.gitem,
        gitem_name: order.gitem_name || '',
        width: order.width,
        length: order.length,
        request_amount: order.request_amount,
        due_date: order.due_date.split('T')[0] // Convert to YYYY-MM-DD format
      });
    }
  }, [order]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value
    }));

    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.po_no.trim()) {
      newErrors.po_no = 'P/O NO는 필수입니다.';
    }

    if (!formData.gitem.trim()) {
      newErrors.gitem = 'GITEM은 필수입니다.';
    }

    if (formData.width <= 0) {
      newErrors.width = '너비는 0보다 커야 합니다.';
    }

    if (formData.length <= 0) {
      newErrors.length = '길이는 0보다 커야 합니다.';
    }

    if (formData.request_amount <= 0) {
      newErrors.request_amount = '의뢰량은 0보다 커야 합니다.';
    }

    if (!formData.due_date) {
      newErrors.due_date = '납기일은 필수입니다.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    onSubmit({
      ...formData,
      due_date: new Date(formData.due_date).toISOString()
    });
  };

  return (
    <div className="modal-overlay">
      <div className="order-form-modal">
        <div className="form-header">
          <h3>{order ? '주문 수정' : '새 주문 추가'}</h3>
          <button className="close-btn" onClick={onCancel}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="order-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="po_no">P/O NO *</label>
              <input
                type="text"
                id="po_no"
                name="po_no"
                value={formData.po_no}
                onChange={handleInputChange}
                className={errors.po_no ? 'error' : ''}
                placeholder="PO-2025-001"
              />
              {errors.po_no && <span className="error-text">{errors.po_no}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="gitem">GITEM *</label>
              <input
                type="text"
                id="gitem"
                name="gitem"
                value={formData.gitem}
                onChange={handleInputChange}
                className={errors.gitem ? 'error' : ''}
                placeholder="GT001"
              />
              {errors.gitem && <span className="error-text">{errors.gitem}</span>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="gitem_name">제품명</label>
              <input
                type="text"
                id="gitem_name"
                name="gitem_name"
                value={formData.gitem_name}
                onChange={handleInputChange}
                placeholder="제품명 (선택사항)"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="width">너비 (mm) *</label>
              <input
                type="number"
                id="width"
                name="width"
                value={formData.width}
                onChange={handleInputChange}
                className={errors.width ? 'error' : ''}
                min="0"
                step="0.1"
              />
              {errors.width && <span className="error-text">{errors.width}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="length">길이 (mm) *</label>
              <input
                type="number"
                id="length"
                name="length"
                value={formData.length}
                onChange={handleInputChange}
                className={errors.length ? 'error' : ''}
                min="0"
                step="0.1"
              />
              {errors.length && <span className="error-text">{errors.length}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="request_amount">의뢰량 *</label>
              <input
                type="number"
                id="request_amount"
                name="request_amount"
                value={formData.request_amount}
                onChange={handleInputChange}
                className={errors.request_amount ? 'error' : ''}
                min="1"
                step="1"
              />
              {errors.request_amount && <span className="error-text">{errors.request_amount}</span>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="due_date">납기일 *</label>
              <input
                type="date"
                id="due_date"
                name="due_date"
                value={formData.due_date}
                onChange={handleInputChange}
                className={errors.due_date ? 'error' : ''}
              />
              {errors.due_date && <span className="error-text">{errors.due_date}</span>}
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              취소
            </button>
            <button type="submit" className="btn btn-primary">
              {order ? '수정' : '추가'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default OrderForm;