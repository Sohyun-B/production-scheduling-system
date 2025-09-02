import React, { useState, useEffect } from 'react';
import { apiService, Order } from '../services/api';
import OrderForm from './OrderForm';
import './OrderTable.css';

const OrderTable: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const ordersData = await apiService.getOrders();
      setOrders(ordersData);
      setError(null);
    } catch (err) {
      setError('주문 데이터 로드에 실패했습니다.');
      console.error('Error loading orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrder = () => {
    setEditingOrder(null);
    setShowForm(true);
  };

  const handleEditOrder = (order: Order) => {
    setEditingOrder(order);
    setShowForm(true);
  };

  const handleDeleteOrder = async (id: number) => {
    if (window.confirm('정말로 이 주문을 삭제하시겠습니까?')) {
      try {
        await apiService.deleteOrder(id);
        loadOrders();
      } catch (err) {
        setError('주문 삭제에 실패했습니다.');
        console.error('Error deleting order:', err);
      }
    }
  };

  const handleFormSubmit = async (orderData: Omit<Order, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      if (editingOrder) {
        await apiService.updateOrder(editingOrder.id, orderData);
      } else {
        await apiService.createOrder(orderData);
      }
      setShowForm(false);
      setEditingOrder(null);
      loadOrders();
    } catch (err) {
      setError('주문 저장에 실패했습니다.');
      console.error('Error saving order:', err);
    }
  };

  const handleFormCancel = () => {
    setShowForm(false);
    setEditingOrder(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR');
  };

  if (loading) return <div className="loading">주문 데이터 로딩 중...</div>;

  return (
    <div className="order-table-container">
      <div className="table-header">
        <h2>주문 관리</h2>
        <div className="table-actions">
          <button className="btn btn-primary" onClick={handleCreateOrder}>
            새 주문 추가
          </button>
          <span className="order-count">총 {orders.length}개 주문</span>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showForm && (
        <OrderForm
          order={editingOrder}
          onSubmit={handleFormSubmit}
          onCancel={handleFormCancel}
        />
      )}

      <div className="table-container">
        <table className="order-table">
          <thead>
            <tr>
              <th>P/O NO</th>
              <th>GITEM</th>
              <th>제품명</th>
              <th>너비</th>
              <th>길이</th>
              <th>의뢰량</th>
              <th>납기일</th>
              <th>생성일</th>
              <th>작업</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan={9} className="no-data">
                  등록된 주문이 없습니다.
                </td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr key={order.id}>
                  <td className="po-no">{order.po_no}</td>
                  <td className="gitem">{order.gitem}</td>
                  <td className="gitem-name">{order.gitem_name || '-'}</td>
                  <td className="width">{order.width}</td>
                  <td className="length">{order.length}</td>
                  <td className="amount">{order.request_amount.toLocaleString()}</td>
                  <td className="due-date">{formatDate(order.due_date)}</td>
                  <td className="created-at">{formatDate(order.created_at)}</td>
                  <td className="actions">
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleEditOrder(order)}
                    >
                      수정
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDeleteOrder(order.id)}
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OrderTable;