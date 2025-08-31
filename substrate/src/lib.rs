#![cfg_attr(not(feature = "std"), no_std, no_main)]

#[ink::contract]
mod simple_deployer {
    use ink::prelude::string::String;
    use ink::prelude::vec::Vec;

    #[ink(storage)]
    pub struct SimpleDeployer {
        owner: AccountId,
        function_count: u32,
    }

    #[ink(event)]
    pub struct FunctionDeployed {
        #[ink(topic)]
        function_id: u32,
        name: String,
    }

    impl SimpleDeployer {
        #[ink(constructor)]
        pub fn new() -> Self {
            Self {
                owner: Self::env().caller(),
                function_count: 0,
            }
        }

        #[ink(message)]
        pub fn deploy_function(&mut self, name: String) -> u32 {
            self.function_count += 1;

            self.env().emit_event(FunctionDeployed {
                function_id: self.function_count,
                name,
            });

            self.function_count
        }

        #[ink(message)]
        pub fn get_function_count(&self) -> u32 {
            self.function_count
        }

        #[ink(message)]
        pub fn get_owner(&self) -> AccountId {
            self.owner
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[ink::test]
        fn deploy_function_works() {
            let mut contract = SimpleDeployer::new();
            let id = contract.deploy_function("test_function".to_string());
            assert_eq!(id, 1);
            assert_eq!(contract.get_function_count(), 1);
        }
    }
}
