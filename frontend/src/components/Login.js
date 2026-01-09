import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Mail, Lock, ArrowLeft, KeyRound, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Login = () => {
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // Forgot password states
  const [forgotPasswordMode, setForgotPasswordMode] = useState(false);
  const [forgotPasswordStep, setForgotPasswordStep] = useState(1); // 1: email, 2: otp, 3: new password
  const [forgotEmail, setForgotEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setLoading(false);
  };

  // State for dev OTP display
  const [devOtp, setDevOtp] = useState('');

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      await axios.post(`${API_URL}/api/auth/forgot-password`, { email: forgotEmail });
      setSuccessMessage('Password reset request submitted. Please contact your partner for the OTP.');
      setForgotPasswordStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      await axios.post(`${API_URL}/api/auth/verify-otp`, { email: forgotEmail, otp });
      setSuccessMessage('OTP verified! Please set your new password.');
      setForgotPasswordStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters');
      setLoading(false);
      return;
    }

    try {
      await axios.post(`${API_URL}/api/auth/reset-password`, {
        email: forgotEmail,
        otp,
        new_password: newPassword
      });
      setSuccessMessage('Password reset successful! You can now login.');
      // Reset all states and go back to login
      setTimeout(() => {
        resetForgotPassword();
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetForgotPassword = () => {
    setForgotPasswordMode(false);
    setForgotPasswordStep(1);
    setForgotEmail('');
    setOtp('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setSuccessMessage('');
  };

  // Forgot Password Flow UI
  if (forgotPasswordMode) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <div className="flex justify-center mb-6">
            <img 
              src="/taskact-logo.svg" 
              alt="TaskAct" 
              className="h-12 w-auto"
            />
          </div>
          <h2 className="text-center text-xl text-gray-600">
            {forgotPasswordStep === 1 && 'Reset Your Password'}
            {forgotPasswordStep === 2 && 'Enter OTP'}
            {forgotPasswordStep === 3 && 'Set New Password'}
          </h2>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
            {/* Back Button */}
            <button
              onClick={resetForgotPassword}
              className="flex items-center text-gray-600 hover:text-gray-900 mb-6 text-sm"
              data-testid="back-to-login"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to Login
            </button>

            {/* Progress Steps */}
            <div className="flex items-center justify-center mb-8">
              {[1, 2, 3].map((step) => (
                <React.Fragment key={step}>
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      forgotPasswordStep >= step
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {step}
                  </div>
                  {step < 3 && (
                    <div
                      className={`w-12 h-1 ${
                        forgotPasswordStep > step ? 'bg-indigo-600' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                <div className="text-sm text-red-600">{error}</div>
              </div>
            )}

            {successMessage && (
              <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4">
                <div className="text-sm text-green-600">{successMessage}</div>
              </div>
            )}

            {/* Step 1: Enter Email */}
            {forgotPasswordStep === 1 && (
              <form onSubmit={handleForgotPassword} className="space-y-6">
                <div>
                  <label htmlFor="forgot-email" className="form-label">
                    Email address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      id="forgot-email"
                      type="email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      required
                      className="form-input pl-10"
                      placeholder="Enter your registered email"
                      data-testid="forgot-email-input"
                    />
                  </div>
                  <p className="mt-2 text-sm text-gray-500">
                    We'll send a 6-digit OTP to this email
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full btn-primary"
                  data-testid="send-otp-button"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Sending OTP...
                    </>
                  ) : (
                    'Send OTP'
                  )}
                </button>
              </form>
            )}

            {/* Step 2: Enter OTP */}
            {forgotPasswordStep === 2 && (
              <form onSubmit={handleVerifyOTP} className="space-y-6">
                {/* DEV MODE: Show OTP on screen */}
                {devOtp && (
                  <div className="bg-yellow-50 border border-yellow-300 rounded-md p-4 mb-4">
                    <p className="text-sm text-yellow-800 font-medium">🔧 Dev Mode - Your OTP:</p>
                    <p className="text-3xl font-mono font-bold text-yellow-900 tracking-widest text-center mt-2">{devOtp}</p>
                    <p className="text-xs text-yellow-700 mt-2">This is only shown for testing. In production, OTP will be sent via email.</p>
                  </div>
                )}
                
                <div>
                  <label htmlFor="otp" className="form-label">
                    Enter OTP
                  </label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      id="otp"
                      type="text"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      required
                      maxLength={6}
                      className="form-input pl-10 text-center text-2xl tracking-widest font-mono"
                      placeholder="000000"
                      data-testid="otp-input"
                    />
                  </div>
                  <p className="mt-2 text-sm text-gray-500">
                    Enter the 6-digit code sent to {forgotEmail}
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={loading || otp.length !== 6}
                  className="w-full btn-primary"
                  data-testid="verify-otp-button"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Verifying...
                    </>
                  ) : (
                    'Verify OTP'
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setForgotPasswordStep(1);
                    setOtp('');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className="w-full text-sm text-indigo-600 hover:text-indigo-500"
                  data-testid="resend-otp-button"
                >
                  Didn't receive OTP? Send again
                </button>
              </form>
            )}

            {/* Step 3: Set New Password */}
            {forgotPasswordStep === 3 && (
              <form onSubmit={handleResetPassword} className="space-y-6">
                <div>
                  <label htmlFor="new-password" className="form-label">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      id="new-password"
                      type={showPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={6}
                      className="form-input pl-10 pr-10"
                      placeholder="Enter new password"
                      data-testid="new-password-input"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="confirm-password" className="form-label">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      id="confirm-password"
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      minLength={6}
                      className="form-input pl-10"
                      placeholder="Confirm new password"
                      data-testid="confirm-password-input"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full btn-primary"
                  data-testid="reset-password-button"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Resetting Password...
                    </>
                  ) : (
                    'Reset Password'
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Regular Login UI
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex justify-center mb-6">
          <img 
            src="/taskact-logo.svg" 
            alt="TaskAct" 
            className="h-12 w-auto"
          />
        </div>
        <h2 className="text-center text-xl text-gray-600">
          Sign in to your account
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <div className="text-sm text-red-600">{error}</div>
              </div>
            )}

            <div>
              <label htmlFor="email" className="form-label">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="form-input"
                data-testid="email-input"
              />
            </div>

            <div>
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="form-input"
                data-testid="password-input"
              />
            </div>

            {/* Forgot Password Link */}
            <div className="flex items-center justify-end">
              <button
                type="button"
                onClick={() => setForgotPasswordMode(true)}
                className="text-sm text-indigo-600 hover:text-indigo-500"
                data-testid="forgot-password-link"
              >
                Forgot password?
              </button>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary"
                data-testid="login-button"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
