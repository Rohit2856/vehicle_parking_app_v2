const { createApp } = Vue;

createApp({
    data() {
        return {
            user: null,
            token: localStorage.getItem('token'),
            activeTab: 'dashboard',
            error: '',
            showRegister: false,
            loginForm: {
                username: '',
                password: ''
            },
            registerForm: {
                username: '',
                password: ''
            },
            dashboardData: null,
            availableLots: [],
            parkingHistory: [],
            currentReservation: null
        }
    },
    mounted() {
        if (this.token) {
            this.verifyToken();
        }
    },
    methods: {
        async login() {
            try {
                const response = await axios.post('http://localhost:5000/auth/login', this.loginForm);
                this.token = response.data.access_token;
                this.user = response.data.user;
                localStorage.setItem('token', this.token);
                this.error = '';
                
                if (this.user.role === 'user') {
                    this.fetchDashboard();
                    this.fetchCurrentReservation();
                }
            } catch (error) {
                this.error = error.response?.data?.error || 'Login failed';
            }
        },
        
        async register() {
            try {
                const response = await axios.post('http://localhost:5000/auth/register', this.registerForm);
                this.showRegister = false;
                this.registerForm = { username: '', password: '' };
                alert('Registration successful! Please login.');
            } catch (error) {
                alert('Registration failed: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        async verifyToken() {
            try {
                const response = await axios.get('http://localhost:5000/auth/verify', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.user = response.data.user;
                
                if (this.user.role === 'user') {
                    this.fetchDashboard();
                    this.fetchCurrentReservation();
                }
            } catch (error) {
                this.logout();
            }
        },
        
        logout() {
            this.user = null;
            this.token = null;
            localStorage.removeItem('token');
        },
        
        async fetchDashboard() {
            try {
                const response = await axios.get('http://localhost:5000/user/dashboard', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.dashboardData = response.data;
            } catch (error) {
                console.error('Failed to fetch dashboard:', error);
            }
        },
        
        async fetchAvailableLots() {
            try {
                const response = await axios.get('http://localhost:5000/user/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.availableLots = response.data.available_lots;
            } catch (error) {
                console.error('Failed to fetch available lots:', error);
            }
        },
        
        async fetchHistory() {
            try {
                const response = await axios.get('http://localhost:5000/user/history', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingHistory = response.data.history;
            } catch (error) {
                console.error('Failed to fetch history:', error);
            }
        },
        
        async fetchCurrentReservation() {
            try {
                const response = await axios.get('http://localhost:5000/user/current-reservation', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.currentReservation = response.data.active_reservation;
            } catch (error) {
                console.error('Failed to fetch current reservation:', error);
            }
        },
        
        async reserveSpot(lotId) {
            try {
                const response = await axios.post('http://localhost:5000/user/reserve', 
                    { lot_id: lotId }, 
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                
                alert('Spot reserved successfully!');
                this.fetchCurrentReservation();
                this.fetchAvailableLots();
                this.fetchDashboard();
            } catch (error) {
                alert('Reservation failed: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        async releaseSpot(reservationId) {
            if (confirm('Are you sure you want to release this parking spot?')) {
                try {
                    const response = await axios.post(`http://localhost:5000/user/release/${reservationId}`, {}, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    
                    alert(`Spot released successfully! Cost: $${response.data.parking_cost}`);
                    this.currentReservation = null;
                    this.fetchDashboard();
                    this.fetchHistory();
                } catch (error) {
                    alert('Release failed: ' + (error.response?.data?.error || 'Unknown error'));
                }
            }
        },
        
        formatDateTime(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleString();
        }
    }
}).mount('#app');
