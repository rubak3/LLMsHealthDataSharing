// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import "./DataExchange.sol";

contract ConsentManager {

    DataExchange immutable dataSC;
    uint256 consentID;

    constructor(address dataSCAddr) {
        dataSC = DataExchange(dataSCAddr);
        consentID = 0;
    }

    struct GovernmentConsent {
        uint256[] dataType;
        uint256[] purpose;
        address receiverAddress;
        bool active;
        uint256 consentID;
        uint validUntil;
    }

    struct GeneralConsent {
        uint256[] dataType;
        uint256[] purpose;
        string[] receiverLocation;
        bool anonymityLevel;
        bool active;
        uint256 consentID;
        uint validUntil;
    }

    struct SpecificConsent {
        address receiverAddress;
        uint256[] dataType;
        uint256[] purpose;
        bool anonymityLevel;
        bool active;
        uint256 consentID;
        uint validUntil;
    }

    struct ConsentRequest {
        address receiver;
        uint256[] dataTypes;
        uint256[] purposes;
    }

    modifier onlyRegisteredUsers {
        require(dataSC.isUserRegistered(msg.sender), "Only registered users can call this function");
        _;
    }

    mapping(address => GovernmentConsent[]) public governmentConsents;
    mapping(address => GeneralConsent[]) public hospitalConsents;
    mapping(address => GeneralConsent[]) public insuranceConsents;
    mapping(address => GeneralConsent[]) public labConsents;   
    mapping(address => GeneralConsent[]) public broadConsents;
    mapping(address => SpecificConsent[]) public specificConsents;
    mapping(address => ConsentRequest[]) public governmentConsentRequests;
    mapping(address => ConsentRequest[]) public patientConsentRequests;

    event NewGovernmentConsentRequested(address governmentAddress);
    event NewGovernmentConsentAdded(address governmentAddress, uint256 consentID);
    event NewPatientConsentRequested(address patientAddress);
    event NewPatientConsentAdded(address patientAddress, uint256 consentID);
    event NewSpecificPatientConsentAdded(address patientAddress, address receiverAddress, uint256 consentID);

    // Functions for adding consents
    function addGovernmentConsent(uint256[] memory dataTypes, uint256[] memory purposes, address receiverAddress, uint validUntil) public onlyRegisteredUsers {
        require(dataSC.getUserRole(msg.sender) == DataExchange.Role.Government, "Only governments can call this function");
        governmentConsents[msg.sender].push(GovernmentConsent({ 
            dataType: dataTypes, 
            purpose: purposes, 
            receiverAddress: receiverAddress,
            active: true,
            consentID: consentID,
            validUntil: validUntil
        }));
        emit NewGovernmentConsentAdded(msg.sender, consentID);
        consentID++;
    }

    function addHospitalConsent(uint256[] memory dataTypes, uint256[] memory purposes, string[] memory receiverLocation, bool anonymityLevel, uint validUntil) public onlyRegisteredUsers {
        hospitalConsents[msg.sender].push(GeneralConsent({ 
            dataType: dataTypes, 
            purpose: purposes, 
            receiverLocation: receiverLocation,
            anonymityLevel: anonymityLevel, 
            active: true,
            consentID: consentID,
            validUntil: validUntil
        }));
        emit NewPatientConsentAdded(msg.sender, consentID);
        consentID++;
    }

    function addInsuranceConsent(uint256[] memory dataTypes, uint256[] memory purposes, string[] memory receiverLocation, bool anonymityLevel, uint validUntil) public onlyRegisteredUsers {
        insuranceConsents[msg.sender].push(GeneralConsent({ 
            dataType: dataTypes, 
            purpose: purposes, 
            receiverLocation: receiverLocation,
            anonymityLevel: anonymityLevel, 
            active: true,
            consentID: consentID,
            validUntil: validUntil
        }));
        emit NewPatientConsentAdded(msg.sender, consentID);
        consentID++;
    }

    function addLabConsent(uint256[] memory dataTypes, uint256[] memory purposes, string[] memory receiverLocation, bool anonymityLevel, uint validUntil) public onlyRegisteredUsers {
        labConsents[msg.sender].push(GeneralConsent({ 
            dataType: dataTypes, 
            purpose: purposes, 
            receiverLocation: receiverLocation,
            anonymityLevel: anonymityLevel, 
            active: true,
            consentID: consentID,
            validUntil: validUntil
        }));
        emit NewPatientConsentAdded(msg.sender, consentID);
        consentID++;
    }

    function addSpecificConsent(address receiver, uint256[] memory dataTypes, uint256[] memory purposes, bool anonymityLevel, uint validUntil) public onlyRegisteredUsers { 
        specificConsents[msg.sender].push(SpecificConsent({ 
            receiverAddress: receiver, 
            dataType: dataTypes, 
            purpose: purposes, 
            anonymityLevel: anonymityLevel, 
            active: true,
            consentID: consentID,
            validUntil: validUntil
        }));
        emit NewSpecificPatientConsentAdded(msg.sender, receiver, consentID);
        consentID++;
    }

    function addBroadConsent(uint256[] memory dataTypes, uint256[] memory purposes, string[] memory receiverLocation, bool anonymityLevel, uint validUntil) public onlyRegisteredUsers {
        broadConsents[msg.sender].push(GeneralConsent({ 
            dataType: dataTypes, 
            purpose: purposes, 
            receiverLocation: receiverLocation,
            anonymityLevel: anonymityLevel, 
            active: true,
            consentID: consentID,
            validUntil: validUntil
        }));
        emit NewPatientConsentAdded(msg.sender, consentID);
        consentID++;
    }



    // Functions for requesting consents
    function requestGovernmentConsent(address government, address receiver, uint256[] memory dataTypes, uint256[] memory purposes) public {
        require(dataSC.isUserRegistered(government), "Government is not registered");
        require(dataSC.isUserRegistered(receiver), "Receiver is not registered");
        patientConsentRequests[government].push(ConsentRequest({
            receiver: receiver,
            dataTypes: dataTypes,
            purposes: purposes
        }));
        emit NewGovernmentConsentRequested(government);
    }

    function requestPatientConsent(address patient, address receiver, uint256[] memory dataTypes, uint256[] memory purposes) public {
        require(dataSC.isUserRegistered(patient), "Patient is not registered");
        require(dataSC.isUserRegistered(receiver), "Receiver is not registered");
        patientConsentRequests[patient].push(ConsentRequest({
            receiver: receiver,
            dataTypes: dataTypes,
            purposes: purposes
        }));
        emit NewPatientConsentRequested(patient);
    }




    // Functions for revoking consents
    function revokeGovernmentConsent(uint256 consentId) public onlyRegisteredUsers {
        require(dataSC.getUserRole(msg.sender) == DataExchange.Role.Government, "Only governments can call this function");
        GovernmentConsent[] storage consents = governmentConsents[msg.sender];
        bool found = false;
        for (uint256 i = 0; i < consents.length; i++) {
            if (consents[i].consentID == consentId) {
                require(consents[i].active, "This consent is already inactive");
                consents[i].active = false;
                found = true;
                break;
            }
        }
        require(found, "Consent ID not found");
    }

    function revokeHospitalConsent(uint256 consentId) public onlyRegisteredUsers {
        GeneralConsent[] storage consents = hospitalConsents[msg.sender];
        bool found = false;
        for (uint256 i = 0; i < consents.length; i++) {
            if (consents[i].consentID == consentId) {
                require(consents[i].active, "This consent is already inactive");
                consents[i].active = false;
                found = true;
                break;
            }
        }
        require(found, "Consent ID not found");
    }

    function revokeInsuranceConsent(uint256 consentId) public onlyRegisteredUsers {
        GeneralConsent[] storage consents = insuranceConsents[msg.sender];
        bool found = false;
        for (uint256 i = 0; i < consents.length; i++) {
            if (consents[i].consentID == consentId) {
                require(consents[i].active, "This consent is already inactive");
                consents[i].active = false;
                found = true;
                break;
            }
        }
        require(found, "Consent ID not found");
    }

    function revokeLabConsent(uint256 consentId) public onlyRegisteredUsers {
        GeneralConsent[] storage consents = labConsents[msg.sender];
        bool found = false;
        for (uint256 i = 0; i < consents.length; i++) {
            if (consents[i].consentID == consentId) {
                require(consents[i].active, "This consent is already inactive");
                consents[i].active = false;
                found = true;
                break;
            }
        }
        require(found, "Consent ID not found");
    }

    function revokeSpecificConsent(uint256 consentId) public onlyRegisteredUsers {
        SpecificConsent[] storage consents = specificConsents[msg.sender];
        bool found = false;
        for (uint256 i = 0; i < consents.length; i++) {
            if (consents[i].consentID == consentId) {
                require(consents[i].active, "This consent is already inactive");
                consents[i].active = false;
                found = true;
                break;
            }
        }
        require(found, "Consent ID not found");
    }

    function revokeBroadConsent(uint256 consentId) public onlyRegisteredUsers {
        GeneralConsent[] storage consents = broadConsents[msg.sender];
        bool found = false;
        for (uint256 i = 0; i < consents.length; i++) {
            if (consents[i].consentID == consentId) {
                require(consents[i].active, "This consent is already inactive");
                consents[i].active = false;
                found = true;
                break;
            }
        }
        require(found, "Consent ID not found");
    }



    // Functions to get consents
    function getGovernmentConsents(address government, address receiver) public view returns (GovernmentConsent[] memory) {
        GovernmentConsent[] storage allConsents = governmentConsents[government];
        uint256 activeCount = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active && allConsents[i].receiverAddress == receiver) {
                activeCount++;
            }
        }
        GovernmentConsent[] memory activeConsents = new GovernmentConsent[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeConsents[index] = allConsents[i];
                index++;
            }
        }
        return activeConsents;
    }

    function getHospitalConsents(address patient) public view returns (GeneralConsent[] memory) {
        GeneralConsent[] storage allConsents = hospitalConsents[patient];
        uint256 activeCount = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeCount++;
            }
        }
        GeneralConsent[] memory activeConsents = new GeneralConsent[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeConsents[index] = allConsents[i];
                index++;
            }
        }
        return activeConsents;
    }

    function getInsuranceConsents(address patient) public view returns (GeneralConsent[] memory) {
        GeneralConsent[] storage allConsents = insuranceConsents[patient];
        uint256 activeCount = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeCount++;
            }
        }
        GeneralConsent[] memory activeConsents = new GeneralConsent[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeConsents[index] = allConsents[i];
                index++;
            }
        }
        return activeConsents;
    }

    function getLabConsents(address patient) public view returns (GeneralConsent[] memory) {
        GeneralConsent[] storage allConsents = labConsents[patient];
        uint256 activeCount = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeCount++;
            }
        }
        GeneralConsent[] memory activeConsents = new GeneralConsent[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeConsents[index] = allConsents[i];
                index++;
            }
        }
        return activeConsents;
    }

    function getSpecificConsents(address patient, address receiver) public view returns (SpecificConsent[] memory) {
        SpecificConsent[] storage allConsents = specificConsents[patient];
        uint256 activeCount = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active && allConsents[i].receiverAddress == receiver) {
                activeCount++;
            }
        }
        SpecificConsent[] memory activeConsents = new SpecificConsent[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeConsents[index] = allConsents[i];
                index++;
            }
        }
        return activeConsents;
    }

    function getBroadConsents(address patient) public view returns (GeneralConsent[] memory) {
        GeneralConsent[] storage allConsents = broadConsents[patient];
        uint256 activeCount = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeCount++;
            }
        }
        GeneralConsent[] memory activeConsents = new GeneralConsent[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allConsents.length; i++) {
            if (allConsents[i].active) {
                activeConsents[index] = allConsents[i];
                index++;
            }
        }
        return activeConsents;
    }
}
