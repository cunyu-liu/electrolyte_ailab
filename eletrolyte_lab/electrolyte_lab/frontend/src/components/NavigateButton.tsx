import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from 'antd';

interface NavigateButtonProps {
  to: string;
  type?: 'primary' | 'default';
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const NavigateButton: React.FC<NavigateButtonProps> = ({ to, type = 'default', children, style }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    console.log(`Navigate to: ${to}`);
    navigate(to);
  };

  return (
    <Button
      type={type}
      onClick={handleClick}
      style={style}
    >
      {children}
    </Button>
  );
};

export default NavigateButton;
