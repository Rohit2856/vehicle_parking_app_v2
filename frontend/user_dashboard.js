const { createApp } = Vue;

createApp({
    data() {
        return {
            user: null,
            token: localStorage.getItem('token'),
            activeTab: 'dashboard',
            error: '',
            showRegister: false,
            registerForm: {
                username: '',
                password: ''
            },
            dashboardData: null,
            availableLots: [],
            parkingHistory: [],
            currentReservation: null,
            userAnalytics: null,
            userCharts: {
                monthlyActivity: null,
                monthlySpending: null,
                durationPreferences: null,
                lotUsage: null,
            isLoading: false
            }
        }
    },
    mounted() {
        if (this.token) {
            this.verifyToken();
        }
    },
    methods: {
        async register() {
            try {
                const response = await axios.post('/auth/register', this.registerForm);
                this.showRegister = false;
                this.registerForm = { username: '', password: '' };
                alert('Registration successful! Please login.');
            } catch (error) {
                alert('Registration failed: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        async verifyToken() {
            try {
                const response = await axios.get('/auth/verify', {
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
            window.location.href = 'index.html'
        },
        
        async fetchDashboard() {
            try {
                const response = await axios.get('/user/dashboard', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.dashboardData = response.data;
            } catch (error) {
                console.error('Failed to fetch dashboard:', error);
            }
        },
        
        async fetchAvailableLots() {
            try {
                const response = await axios.get('/user/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.availableLots = response.data.available_lots;
            } catch (error) {
                console.error('Failed to fetch available lots:', error);
            }
        },
        
        async fetchHistory() {
            try {
                const response = await axios.get('/user/history', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingHistory = response.data.history;
            } catch (error) {
                console.error('Failed to fetch history:', error);
            }
        },
        
        async fetchCurrentReservation() {
            try {
                const response = await axios.get('/user/current-reservation', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.currentReservation = response.data.active_reservation;
            } catch (error) {
                console.error('Failed to fetch current reservation:', error);
            }
        },
        
        async reserveSpot(lotId) {
            try {
                const response = await axios.post('/user/reserve', 
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
                    const response = await axios.post(`/user/release/${reservationId}`, {}, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    
                    alert(`Spot released successfully! Cost: ₹${response.data.parking_cost}`);
                    this.currentReservation = null;
                    this.fetchDashboard();
                    this.fetchHistory();
                } catch (error) {
                    alert('Release failed: ' + (error.response?.data?.error || 'Unknown error'));
                }
            }
        },
        
        async fetchUserAnalytics() {
            try {
                const response = await axios.get('/analytics/user/parking-stats', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                console.log('Analytics response:', response.data);
                this.userAnalytics = response.data;

                // Waiting for Vue to update the DOM
                await this.$nextTick();
                
                // Additional delay for canvas elements to be fully rendered
                setTimeout(() => {
                    this.createUserCharts();
                }, 200);
                
            } catch (error) {
                console.error('Failed to fetch user analytics:', error);
            }
        },
        async exportMyData() {
            try {
                const response = await axios.post('/jobs/trigger-csv-export', {
                    user_id: this.user.id,
                    export_type: 'user'
                }, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                // Poll for completion and download
                this.pollForDownload(response.data.job_id);
                
            } catch (error) {
                alert('Export failed: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },

        async pollForDownload(jobId) {
            const checkStatus = async () => {
                try {
                    const statusResponse = await axios.get(`/jobs/status/${jobId}`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    
                    if (statusResponse.data.state === 'SUCCESS') {
                        // Download the file
                        const downloadUrl = `/export/csv/download/${jobId}?user_id=${this.user.id}&export_type=user`;
                        const link = document.createElement('a');
                        link.href = downloadUrl;
                        link.download = 'my_parking_history.csv';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    } else if (statusResponse.data.state === 'FAILURE') {
                        alert('Export failed');
                    } else {
                        setTimeout(checkStatus, 2000);
                    }
                } catch (error) {
                    console.error('Status check failed:', error);
                }
            };
            
            checkStatus();
        },

        async createUserCharts() {
            if (!this.userAnalytics) return;

            // Waiting for Vue DOM updates
            await this.$nextTick();
            
            // Additional delay to ensure canvas elements are fully rendered
            setTimeout(() => {
                this.createUserMonthlyActivityChart();
                this.createUserMonthlySpendingChart();
                this.createUserDurationPreferencesChart();
                this.createUserLotUsageChart();
            }, 500); 
        },

        createUserMonthlyActivityChart() {
            const canvas = document.getElementById('userMonthlyActivityChart');
            if (!canvas) {
                console.error('Canvas userMonthlyActivityChart not found');
                setTimeout(() => this.createUserMonthlyActivityChart(), 100);
                return;
            }
            
            const ctx = canvas.getContext('2d');
            
            if (this.userCharts.monthlyActivity) {
                this.userCharts.monthlyActivity.destroy();
            }
            
            const activityData = this.userAnalytics.monthly_activity || [];
            
            this.userCharts.monthlyActivity = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: activityData.map(m => m.month),
                    datasets: [{
                        label: 'Monthly Reservations',
                        data: activityData.map(m => m.reservations),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },

        createUserMonthlySpendingChart() {
            const ctx = document.getElementById('userMonthlySpendingChart').getContext('2d');
            if (this.userCharts.monthlySpending) {
                this.userCharts.monthlySpending.destroy();
            }
            
            this.userCharts.monthlySpending = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: this.userAnalytics.monthly_spending.map(m => m.month),
                    datasets: [{
                        label: 'Monthly Spending (₹)',
                        data: this.userAnalytics.monthly_spending.map(m => m.spending),
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },
        
        createUserDurationPreferencesChart() {
            const ctx = document.getElementById('userDurationPreferencesChart').getContext('2d');
            if (this.userCharts.durationPreferences) {
                this.userCharts.durationPreferences.destroy();
            }
            
            this.userCharts.durationPreferences = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: this.userAnalytics.duration_preferences.map(d => d.label),
                    datasets: [{
                        data: this.userAnalytics.duration_preferences.map(d => d.count),
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.5)',
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 205, 86, 0.5)',
                            'rgba(75, 192, 192, 0.5)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 205, 86, 1)',
                            'rgba(75, 192, 192, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        },
        
        createUserLotUsageChart() {
            const ctx = document.getElementById('userLotUsageChart').getContext('2d');
            if (this.userCharts.lotUsage) {
                this.userCharts.lotUsage.destroy();
            }
            
            this.userCharts.lotUsage = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: this.userAnalytics.lot_usage.map(l => l.lot_name),
                    datasets: [{
                        label: 'Usage Count',
                        data: this.userAnalytics.lot_usage.map(l => l.usage_count),
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },
        
        formatDateTime(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleString();
        }
    }
}).mount('#app');
