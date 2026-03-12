import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

interface PageTransitionProps {
  children: React.ReactNode;
}

// 页面过渡动画组件（纯CSS版本）
const PageTransition: React.FC<PageTransitionProps> = ({ children }) => {
  const location = useLocation();
  const [isAnimating, setIsAnimating] = useState(false);
  const [displayChildren, setDisplayChildren] = useState(children);
  const [animationClass, setAnimationClass] = useState('');

  useEffect(() => {
    setIsAnimating(true);
    setAnimationClass('fade-out');

    // 开始退出动画
    const timer = setTimeout(() => {
      setDisplayChildren(children);
      setAnimationClass('fade-in');

      // 开始进入动画
      const timer2 = setTimeout(() => {
        setIsAnimating(false);
        setAnimationClass('');
      }, 400);

      return () => clearTimeout(timer2);
    }, 200);

    return () => clearTimeout(timer);
  }, [location.pathname, children]);

  return (
    <div
      className={`page-transition-container ${animationClass}`}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        pointerEvents: isAnimating ? 'none' : 'auto',
        ...(animationClass === 'fade-in' && {
          animation: 'fadeIn 0.4s ease-out',
        }),
        ...(animationClass === 'fade-out' && {
          animation: 'fadeOut 0.2s ease-out',
        }),
      }}
    >
      {displayChildren}
    </div>
  );
};

export default PageTransition;