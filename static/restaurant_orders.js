// restaurant_orders.js - Sipariş detayları akordiyon işlevselliği için

document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap'in JavaScript kütüphanesinin yüklenip yüklenmediğini kontrol et
    if (typeof bootstrap !== 'undefined') {
        console.log('Bootstrap JS yüklendi, accordion otomatik çalışacak');
    } else {
        console.log('Bootstrap JS yüklenemedi, manuel kontroller uygulanıyor');
        
        // Accordion başlıklarına olay dinleyicileri ekle
        const accordionButtons = document.querySelectorAll('.accordion-button');
        
        accordionButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Hedef panel
                const targetId = this.getAttribute('data-bs-target');
                const targetPanel = document.querySelector(targetId);
                
                if (!targetPanel) return;
                
                // Başlık düğmesinin durumunu değiştir
                const isCurrentlyExpanded = this.getAttribute('aria-expanded') === 'true';
                
                // Diğer tüm panelleri kapat
                document.querySelectorAll('.accordion-collapse.show').forEach(panel => {
                    if (panel !== targetPanel) {
                        panel.classList.remove('show');
                        // İlgili başlık düğmesini de güncelle
                        const panelId = panel.getAttribute('id');
                        const relatedButton = document.querySelector(`[data-bs-target="#${panelId}"]`);
                        if (relatedButton) {
                            relatedButton.setAttribute('aria-expanded', 'false');
                            relatedButton.classList.add('collapsed');
                        }
                    }
                });
                
                // Hedef panelin durumunu değiştir
                if (isCurrentlyExpanded) {
                    targetPanel.classList.remove('show');
                    this.setAttribute('aria-expanded', 'false');
                    this.classList.add('collapsed');
                } else {
                    targetPanel.classList.add('show');
                    this.setAttribute('aria-expanded', 'true');
                    this.classList.remove('collapsed');
                }
            });
        });
    }
    
    // Sipariş durumu değişikliklerini takip et
    const statusForms = document.querySelectorAll('form[action*="update-status"]');
    statusForms.forEach(form => {
        const statusSelect = form.querySelector('select[name="status"]');
        const originalValue = statusSelect.value;
        
        statusSelect.addEventListener('change', function() {
            if (this.value !== originalValue) {
                const confirmChange = confirm('Sipariş durumunu değiştirmek istediğinizden emin misiniz?');
                if (confirmChange) {
                    form.submit();
                } else {
                    this.value = originalValue;
                }
            }
        });
    });
});