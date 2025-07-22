const { createApp } = Vue;

createApp({
    data() {
        return {
            loginForm: {
                username: '',
                password: ''
            },
            registerForm: {
                username: '',
                password: '',
                email: '',
                full_name: '',
                mobile_number: '',
                vehicle_type: '',
                vehicle_number: '',
                vehicle_brand: '',
                home_address: '',
                agree_terms: false
            },
            showRegister: false,
            isLoading: false,
            registerLoading: false,
            error: '',
            registerError: ''
        }
    },

    methods: {
        async login() {
            this.isLoading = true;
            this.error = '';
            
            try {
                const response = await axios.post('/auth/login', this.loginForm);
                localStorage.setItem('token', response.data.access_token);
                
                if (response.data.user.role === 'admin') {
                    window.location.href = 'admin_dashboard.html';
                } else if (response.data.user.role === 'user') {
                    window.location.href = 'user_dashboard.html';
                } else {
                    throw new Error('Unknown user role');
                }
                
            } catch (error) {
                this.error = error.response?.data?.error || 'Login failed';
            } finally {
                this.isLoading = false;
            }
        },

        async register() {
            this.registerLoading = true;
            this.registerError = '';
            
            try {
                // Client-side validation
                if (!this.validateRegistrationForm()) {
                    return;
                }
                
                const response = await axios.post('/auth/register', {
                    username: this.registerForm.username,
                    password: this.registerForm.password,
                    email: this.registerForm.email,
                    full_name: this.registerForm.full_name,
                    mobile_number: this.registerForm.mobile_number,
                    vehicle_type: this.registerForm.vehicle_type,
                    vehicle_number: this.registerForm.vehicle_number.toUpperCase(),
                    vehicle_brand: this.registerForm.vehicle_brand || null,
                    home_address: this.registerForm.home_address || null
                });
                
                this.showRegister = false;
                this.resetRegisterForm();
                alert('Registration successful! You can now login. We will send parking reminders to your email and Google Chat.');
                
            } catch (error) {
                this.registerError = error.response?.data?.error || 'Registration failed';
            } finally {
                this.registerLoading = false;
            }
        },

        validateRegistrationForm() {
            // Email validation
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailPattern.test(this.registerForm.email)) {
                this.registerError = 'Please enter a valid email address';
                return false;
            }
            
            // Mobile number validation (Indian format)
            const mobilePattern = /^[6-9]\d{9}$/;
            if (!mobilePattern.test(this.registerForm.mobile_number)) {
                this.registerError = 'Please enter a valid 10-digit Indian mobile number starting with 6-9';
                return false;
            }
            
            // Vehicle number validation
            const vehiclePattern = /^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$/;
            if (!vehiclePattern.test(this.registerForm.vehicle_number.toUpperCase())) {
                this.registerError = 'Please enter vehicle number in correct format (e.g., DL01AB1234)';
                return false;
            }
            
            // Gmail recommendation check
            if (!this.registerForm.email.endsWith('@gmail.com')) {
                if (!confirm('We recommend using a Gmail account for better Google Chat integration. Continue with this email?')) {
                    return false;
                }
            }
            
            return true;
        },

        resetRegisterForm() {
            this.registerForm = {
                username: '',
                password: '',
                email: '',
                full_name: '',
                mobile_number: '',
                vehicle_type: '',
                vehicle_number: '',
                vehicle_brand: '',
                home_address: '',
                agree_terms: false
            };
        },
        
    }
}).mount('#app');
