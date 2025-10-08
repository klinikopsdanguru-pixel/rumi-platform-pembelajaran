document.addEventListener('DOMContentLoaded', function() {
    
    // Fitur Intip Password
    const passwordToggles = document.querySelectorAll('.password-toggle-icon');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const passwordInput = document.getElementById(this.getAttribute('data-target'));
            if (passwordInput) {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.classList.remove('fa-eye');
                    this.classList.add('fa-eye-slash');
                } else {
                    passwordInput.type = 'password';
                    this.classList.remove('fa-eye-slash');
                    this.classList.add('fa-eye');
                }
            }
        });
    });

    // Fitur Modal Konten & Pelaporan Progres
    const contentModal = document.getElementById('contentModal');
    if (contentModal) {
        document.body.addEventListener('click', function(event) {
            const button = event.target.closest('.view-content-btn');
            if (button) {
                event.preventDefault();
                
                const contentUrl = button.getAttribute('data-url');
                const contentTitle = button.getAttribute('data-title');
                const kontenId = button.getAttribute('data-konten-id');

                fetch(`/konten/${kontenId}/selesai`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        const modalTitle = contentModal.querySelector('.modal-title');
                        const contentFrame = contentModal.querySelector('#contentFrame');
                        modalTitle.textContent = contentTitle;
                        contentFrame.src = contentUrl;
                        
                        const modal = new bootstrap.Modal(contentModal);
                        modal.show();

                        contentModal.addEventListener('hidden.bs.modal', function () {
                            location.reload();
                        }, { once: true });
                    }
                })
                .catch(error => console.error('Error:', error));
            }
        });

        // Mengosongkan iframe saat modal ditutup
        contentModal.addEventListener('hidden.bs.modal', function () {
            const contentFrame = contentModal.querySelector('#contentFrame');
            if (contentFrame) {
                contentFrame.src = "about:blank";
            }
        });
    }

    // Fitur Dropdown Konten Dinamis
    const alurSelect = document.getElementById('alur');
    const tipeSelect = document.getElementById('tipe');
    if (alurSelect && tipeSelect) {
        const contentOptions = {
            'memahami': ['Bacaan (PDF/Slide)', 'Video', 'Audio', 'Peta Konsep', 'Infografis'],
            'mengaplikasi': ['Kuis', 'Simulasi Virtual', 'Studi Kasus', 'Proyek Kolaboratif'],
            'merefleksi': ['Jurnal Refleksi', 'Diskusi Terpandu']
        };

        function updateTipeOptions() {
            const selectedAlur = alurSelect.value;
            const currentTipeValue = tipeSelect.value;
            tipeSelect.innerHTML = '';

            const options = contentOptions[selectedAlur] || [];
            
            options.forEach(optionValue => {
                const option = document.createElement('option');
                option.value = optionValue;
                option.textContent = optionValue;
                tipeSelect.appendChild(option);
            });

            if (options.includes(currentTipeValue)) {
                tipeSelect.value = currentTipeValue;
            }
        }
        alurSelect.addEventListener('change', updateTipeOptions);
        updateTipeOptions();
    }

    // Fitur Notifikasi Hilang Otomatis
    const autoDismissAlerts = document.querySelectorAll('.alert.alert-dismissible');
    autoDismissAlerts.forEach(function(alert) {
        setTimeout(function() {
            new bootstrap.Alert(alert).close();
        }, 3000);
    });

    // Fitur PDF di Modal untuk Pojok Baca (Metode Sederhana)
    const readNowButtons = document.querySelectorAll('.read-now-btn');
    readNowButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const pdfUrl = this.getAttribute('href');
            const pdfTitle = this.getAttribute('data-title');
            
            if (contentModal) {
                const modalTitle = contentModal.querySelector('.modal-title');
                const contentFrame = contentModal.querySelector('#contentFrame');
                modalTitle.textContent = pdfTitle;
                contentFrame.src = pdfUrl; 
                
                new bootstrap.Modal(contentModal).show();
            }
        });
    });

    // Fitur Tandai Notifikasi Dibaca
    const notificationDropdown = document.getElementById('notificationDropdown');
    if (notificationDropdown) {
        notificationDropdown.addEventListener('click', function() {
            const unreadBadge = this.querySelector('.badge');
            if (unreadBadge) {
                // Kirim request ke server untuk menandai sudah dibaca
                fetch('/notifikasi/baca', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                }).then(response => response.json())
                  .then(data => {
                      if (data.status === 'ok') {
                          // Hilangkan badge angka setelah diklik
                          unreadBadge.remove();
                      }
                  });
            }
        });
    }
});