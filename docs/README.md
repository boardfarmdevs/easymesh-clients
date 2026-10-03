# The clients' documents

[Repository](../README.md) · [Site](https://vcpe.dev/easymesh-clients/)

The [site](https://vcpe.dev/easymesh-clients/) introduces the labs' Wi-Fi clients, for a
newcomer. These documents go further:

| Document | Kind | What it covers |
| --- | --- | --- |
| [What devices document about roaming](reference/documented-roaming.md) | reference | the sources for client models: Apple, Pixel, Galaxy, Intel, iwd and wpa_supplicant 2.12, each value with its confidence |
| [The clients of each lab](reference/lab-clients.md) | reference | every lab's clients as they are built today: image, supplicant, configuration, address, pool, start gates, and everything that reaches into a client |
| [Client models: requirements and design](proposals/client-models.md) | proposal | clients that roam like an iPhone, iPad, Mac, Pixel, Galaxy, Windows laptop or iwd device: the requirements, the catalog, the values, one wpa_supplicant 2.12 build and its patch series, iwd, the model file, the steps |
| [Roaming test plan](project/roaming-test-plan.md) | project | the bench (hwsim, two access points, the medium's wmediumd) and the tests that check each model's trigger, margin, load trigger and BTM answers |
| [More capable clients](proposals/more-capable-clients.md) | proposal | a written contract, named actions (such as traffic between two clients), client models and behaviours; how they stay backward compatible; when the clients' code is worth sharing |
