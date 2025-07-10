const { createApp } = Vue;

createApp({
    data() {
        return {
            user: null,
            token: localStorage.getItem('token'),
            activeTab: 'overview',
            error: '',
            loginForm: {
                username: '',
                password: ''
            },
            dashboardSummary: null,
            parkingLots: [],
            parkingSpots: [],
            users: [],
            showCreateLotModal: false,
            newLot: {
                prime_location_name: '',
                price: '',
                address: '',
                pin_code: '',
                number_of_spots: ''
            }
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
                
                if (this.user.role === 'admin') {
                    this.fetchDashboardSummary();
                }
            } catch (error) {
                this.error = error.response?.data?.error || 'Login failed';
            }
        },
        
        async verifyToken() {
            try {
                const response = await axios.get('http://localhost:5000/auth/verify', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.user = response.data.user;
                
                if (this.user.role === 'admin') {
                    this.fetchDashboardSummary();
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
        
        async fetchDashboardSummary() {
            try {
                const response = await axios.get('http://localhost:5000/admin/dashboard/summary', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.dashboardSummary = response.data;
            } catch (error) {
                console.error('Failed to fetch dashboard summary:', error);
            }
        },
        
        async fetchParkingLots() {
            try {
                const response = await axios.get('http://localhost:5000/admin/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingLots = response.data.lots;
            } catch (error) {
                console.error('Failed to fetch parking lots:', error);
            }
        },
        
        async fetchParkingSpots() {
            try {
                const response = await axios.get('http://localhost:5000/admin/spots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingSpots = response.data.spots;
            } catch (error) {
                console.error('Failed to fetch parking spots:', error);
            }
        },
        
        async fetchUsers() {
            try {
                const response = await axios.get('http://localhost:5000/admin/users', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.users = response.data.users;
            } catch (error) {
                console.error('Failed to fetch users:', error);
            }
        },
        
        async createParkingLot() {
            try {
                const response = await axios.post('http://localhost:5000/admin/lots', this.newLot, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.showCreateLotModal = false;
                this.newLot = {
                    prime_location_name: '',
                    price: '',
                    address: '',
                    pin_code: '',
                    number_of_spots: ''
                };
                this.fetchParkingLots();
                alert('Parking lot created successfully!');
            } catch (error) {
                alert('Failed to create parking lot: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        async deleteLot(lotId) {
            if (confirm('Are you sure you want to delete this parking lot?')) {
                try {
                    await axios.delete(`http://localhost:5000/admin/lots/${lotId}`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    this.fetchParkingLots();
                    alert('Parking lot deleted successfully!');
                } catch (error) {
                    alert('Failed to delete parking lot: ' + (error.response?.data?.error || 'Unknown error'));
                }
            }
        },
        
        async viewLotDetails(lotId) {
            try {
                const response = await axios.get(`http://localhost:5000/admin/lots/${lotId}`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                alert(JSON.stringify(response.data.lot_details, null, 2));
            } catch (error) {
                alert('Failed to fetch lot details');
            }
        },
        
        editLot(lot) {
            // Implement edit functionality
            alert('Edit functionality to be implemented');
        }
    }
}).mount('#app');
