// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract DataExchangeManager {
    
    enum Role {Patient, Hospital, ResearchLab, InsuranceCompany, Government}

    modifier onlyRegisteredUsers {
        require(isUserRegistered(msg.sender), "Only registered users can call this function");
        _;
    }

    struct User {
        Role role;
        bytes publicKey;
        bytes AESKey;
        string country;
        bool registered;
    }

    struct Data {
        address sender;
        address patient;
        bytes data;
        bytes audit;
        uint256 timestamp;
    }

    mapping(address => User) public registeredUsers;
    mapping(string => address) public registeredGovernments;
    mapping(address => Data[]) public sharedData;

    event DataShared(address sender, address receiver, address patient, bytes sharedData, bytes summary);

    function registerUser(Role userRole, bytes memory key, bytes memory aesKey, string memory country) public {
        require(!registeredUsers[msg.sender].registered, "User is already registered");
        registeredUsers[msg.sender] = User({
            role: userRole,
            publicKey: key,
            AESKey: aesKey, 
            country: country,
            registered: true
        });
        if (userRole == Role.Government) {
            registeredGovernments[country] = msg.sender;
        }
    }



    function shareData(address receiver, address patient, bytes memory dataHash, bytes memory auditHash) public onlyRegisteredUsers {
        require(registeredUsers[receiver].registered, "Receiver not registered");
        require(registeredUsers[patient].registered, "Patient not registered");
        sharedData[receiver].push(Data(msg.sender, patient, dataHash, auditHash, block.timestamp));
        emit DataShared(msg.sender, receiver, patient, dataHash, auditHash);
    }



    function isUserRegistered(address userAddress) public view returns (bool) {
        return registeredUsers[userAddress].registered;
    }

    function getUserRole(address userAddress) public view returns (Role) {
        return registeredUsers[userAddress].role;
    }

    function getUserCountry(address userAddress) public view returns (string memory) {
        return registeredUsers[userAddress].country;
    }

    function getUserPublicKey(address userAddress) public view returns (bytes memory) {
        return registeredUsers[userAddress].publicKey;
    }

    function getGovernmentAddress(string memory country) public view returns (address) {
        return registeredGovernments[country];
    }

}