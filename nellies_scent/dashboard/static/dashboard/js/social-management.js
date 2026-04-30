const openProviderModalButton = document.getElementById('open-provider-modal');
const providerModal = document.getElementById('provider-modal');
const modalClose = document.getElementById('modal-close');
const modalCancel = document.getElementById('modal-cancel');
const modalTitle = document.getElementById('modal-title');
const providerForm = document.getElementById('provider-form');
const providerSubmit = document.getElementById('provider-submit');

const openEditButtons = document.querySelectorAll('.open-provider-edit');

const toggleModal = (open) => {
    if (!providerModal) return;
    providerModal.classList.toggle('hidden', !open);
};

const clearProviderForm = () => {
    if (!providerForm) return;
    providerForm.reset();
    providerForm.action = providerForm.dataset.createAction || providerForm.action;
    modalTitle.textContent = 'Add social provider';
    providerSubmit.textContent = 'Save provider';
};

const fillProviderForm = (data) => {
    if (!providerForm) return;
    providerForm.action = data.action;
    modalTitle.textContent = 'Edit social provider';
    providerSubmit.textContent = 'Update provider';

    providerForm.querySelector('#id_provider').value = data.provider;
    providerForm.querySelector('#id_name').value = data.name;
    providerForm.querySelector('#id_client_id').value = data.client_id;
    providerForm.querySelector('#id_secret').value = '';
    providerForm.querySelector('#id_key').value = data.key;
    providerForm.querySelector('#id_redirect_uris').value = data.redirect_uris;
    providerForm.querySelector('#id_enabled').checked = data.enabled === 'true';

    const siteValue = data.sites || '';
    const selectedSiteIds = siteValue.split(',').filter(Boolean);
    const sitesSelect = providerForm.querySelector('#id_sites');
    if (sitesSelect) {
        Array.from(sitesSelect.options).forEach((option) => {
            option.selected = selectedSiteIds.includes(option.value);
        });
    }
};

if (providerForm) {
    providerForm.dataset.createAction = providerForm.action;
}

if (openProviderModalButton) {
    openProviderModalButton.addEventListener('click', () => {
        clearProviderForm();
        toggleModal(true);
    });
}

if (modalClose) {
    modalClose.addEventListener('click', () => toggleModal(false));
}

if (modalCancel) {
    modalCancel.addEventListener('click', () => toggleModal(false));
}

if (openEditButtons) {
    openEditButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const data = {
                action: `/dashboard/social/providers/${button.dataset.providerId}/edit/`,
                provider: button.dataset.providerProvider,
                name: button.dataset.providerName,
                client_id: button.dataset.clientId,
                key: button.dataset.key,
                redirect_uris: button.dataset.redirectUris || '',
                enabled: button.dataset.enabled || 'false',
                sites: button.dataset.sites || '',
            };
            fillProviderForm(data);
            toggleModal(true);
        });
    });
}

window.addEventListener('click', (event) => {
    if (!providerModal) return;
    if (event.target === providerModal) {
        toggleModal(false);
    }
});
