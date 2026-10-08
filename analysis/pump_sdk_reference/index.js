"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/index.ts
var index_exports = {};
__export(index_exports, {
  ADMIN_CTO_COMPUTE_UNIT_LIMIT: () => ADMIN_CTO_COMPUTE_UNIT_LIMIT,
  AMM_GLOBAL_PDA: () => AMM_GLOBAL_PDA,
  AMM_GLOBAL_VOLUME_ACCUMULATOR_PDA: () => AMM_GLOBAL_VOLUME_ACCUMULATOR_PDA,
  BONDING_CURVE_NEW_SIZE: () => BONDING_CURVE_NEW_SIZE,
  BONDING_CURVE_SIZE: () => BONDING_CURVE_SIZE,
  CANONICAL_POOL_INDEX: () => CANONICAL_POOL_INDEX,
  CashbackDeprecatedError: () => CashbackDeprecatedError,
  CreatorFeeBpsOutOfRangeError: () => CreatorFeeBpsOutOfRangeError,
  CreatorFeeNotAllowedForCashbackCoinError: () => CreatorFeeNotAllowedForCashbackCoinError,
  CreatorFeeNotConfigurableError: () => CreatorFeeNotConfigurableError,
  CreatorFeeNotConfigurableForQuoteError: () => CreatorFeeNotConfigurableForQuoteError,
  CtoNotAllowedForMayhemCoinError: () => CtoNotAllowedForMayhemCoinError,
  DONATION_RELAY_PROGRAM_ID_DEVNET: () => DONATION_RELAY_PROGRAM_ID_DEVNET,
  DONATION_RELAY_PROGRAM_ID_MAINNET: () => DONATION_RELAY_PROGRAM_ID_MAINNET,
  DuplicateShareholderError: () => DuplicateShareholderError,
  FEE_CONFIG_CURRENT_SIZE: () => FEE_CONFIG_CURRENT_SIZE,
  FEE_CONFIG_INITIALIZE_SIZE: () => FEE_CONFIG_INITIALIZE_SIZE,
  FEE_CONFIG_POST_STABLE_SIZE: () => FEE_CONFIG_POST_STABLE_SIZE,
  FEE_PROGRAM_GLOBAL_PDA: () => FEE_PROGRAM_GLOBAL_PDA,
  GLOBAL_PDA: () => GLOBAL_PDA,
  GLOBAL_SIZE: () => GLOBAL_SIZE,
  GLOBAL_VOLUME_ACCUMULATOR_PDA: () => GLOBAL_VOLUME_ACCUMULATOR_PDA,
  HolderRewardCreatorImmutableError: () => HolderRewardCreatorImmutableError,
  HolderRewardDisabledError: () => HolderRewardDisabledError,
  InvalidShareTotalError: () => InvalidShareTotalError,
  MAYHEM_PROGRAM_ID: () => MAYHEM_PROGRAM_ID,
  NoShareholdersError: () => NoShareholdersError,
  OnlinePumpSdk: () => OnlinePumpSdk,
  PUMP_AMM_EVENT_AUTHORITY_PDA: () => PUMP_AMM_EVENT_AUTHORITY_PDA,
  PUMP_AMM_PROGRAM_ID: () => PUMP_AMM_PROGRAM_ID,
  PUMP_EVENT_AUTHORITY_PDA: () => PUMP_EVENT_AUTHORITY_PDA,
  PUMP_FEE_CONFIG_PDA: () => PUMP_FEE_CONFIG_PDA,
  PUMP_FEE_EVENT_AUTHORITY_PDA: () => PUMP_FEE_EVENT_AUTHORITY_PDA,
  PUMP_FEE_PROGRAM_ID: () => PUMP_FEE_PROGRAM_ID,
  PUMP_PROGRAM_ID: () => PUMP_PROGRAM_ID,
  PUMP_SDK: () => PUMP_SDK,
  Platform: () => Platform,
  PoolRequiredForGraduatedError: () => PoolRequiredForGraduatedError,
  PumpSdk: () => PumpSdk,
  QUOTE_CONTROL_PDA: () => QUOTE_CONTROL_PDA,
  SOL_LIKE_QUOTE_MINTS: () => SOL_LIKE_QUOTE_MINTS,
  STABLE_QUOTE_MINTS: () => STABLE_QUOTE_MINTS,
  ShareCalculationOverflowError: () => ShareCalculationOverflowError,
  TooManyShareholdersError: () => TooManyShareholdersError,
  UnsupportedQuoteMintError: () => UnsupportedQuoteMintError,
  ZeroShareError: () => ZeroShareError,
  ammCreatorVaultPda: () => ammCreatorVaultPda,
  bondingCurveMarketCap: () => bondingCurveMarketCap,
  bondingCurvePda: () => bondingCurvePda,
  bondingCurveV2Pda: () => bondingCurveV2Pda,
  boostVaultAuthorityPda: () => boostVaultAuthorityPda,
  calculateFeeTier: () => calculateFeeTier,
  canonicalPumpPoolPda: () => canonicalPumpPoolPda,
  canonicalPumpPoolPdaWithQuote: () => canonicalPumpPoolPdaWithQuote,
  computeFeesBps: () => computeFeesBps,
  creatorVaultPda: () => creatorVaultPda,
  currentDayTokens: () => currentDayTokens,
  donationFeePda: () => donationFeePda,
  donationRelayDebouncerPda: () => donationRelayDebouncerPda,
  donationRelayEpochTrackerPda: () => donationRelayEpochTrackerPda,
  donationRelayEventAuthorityPda: () => donationRelayEventAuthorityPda,
  donationRelayMintWhitelistPda: () => donationRelayMintWhitelistPda,
  donationRelayPda: () => donationRelayPda,
  feeSharingConfigPda: () => feeSharingConfigPda,
  getBuySolAmountFromTokenAmount: () => getBuySolAmountFromTokenAmount,
  getBuyTokenAmountFromSolAmount: () => getBuyTokenAmountFromSolAmount,
  getEventAuthorityPda: () => getEventAuthorityPda,
  getFee: () => getFee,
  getGlobalParamsPda: () => getGlobalParamsPda,
  getMayhemStatePda: () => getMayhemStatePda,
  getPumpAmmProgram: () => getPumpAmmProgram,
  getPumpFeeProgram: () => getPumpFeeProgram,
  getPumpProgram: () => getPumpProgram,
  getSellSolAmountFromTokenAmount: () => getSellSolAmountFromTokenAmount,
  getSolVaultPda: () => getSolVaultPda,
  getTokenVaultPda: () => getTokenVaultPda,
  hasCoinCreatorMigratedToSharingConfig: () => hasCoinCreatorMigratedToSharingConfig,
  holderRewardsPda: () => holderRewardsPda,
  initialVirtualQuoteReservesFor: () => initialVirtualQuoteReservesFor,
  isExoticQuoteMint: () => isExoticQuoteMint,
  isLegacyQuoteMint: () => isLegacyQuoteMint,
  isSharingConfigEditable: () => isSharingConfigEditable,
  isSolLikeQuoteMint: () => isSolLikeQuoteMint,
  isStableQuoteMint: () => isStableQuoteMint,
  newBondingCurve: () => newBondingCurve,
  normalizeQuoteMint: () => normalizeQuoteMint,
  platformToString: () => platformToString,
  pumpIdl: () => pump_default,
  pumpPoolAuthorityPda: () => pumpPoolAuthorityPda,
  quoteAta: () => quoteAta,
  selectCurveFeeSchedule: () => selectCurveFeeSchedule,
  socialFeePda: () => socialFeePda,
  stringToPlatform: () => stringToPlatform,
  totalUnclaimedTokens: () => totalUnclaimedTokens,
  userVolumeAccumulatorPda: () => userVolumeAccumulatorPda
});
module.exports = __toCommonJS(index_exports);

// src/idl/pump.json
var pump_default = {
  address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
  metadata: {
    name: "pump",
    version: "0.1.0",
    spec: "0.1.0",
    description: "Created with Anchor"
  },
  instructions: [
    {
      name: "add_quote_control_mint",
      discriminator: [
        2,
        14,
        61,
        138,
        170,
        142,
        14,
        95
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "quote_control",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  113,
                  117,
                  111,
                  116,
                  101,
                  45,
                  99,
                  111,
                  110,
                  116,
                  114,
                  111,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "quote_mint",
          type: "pubkey"
        },
        {
          name: "initial_virtual_quote_reserves",
          type: "u64"
        }
      ]
    },
    {
      name: "add_quote_mint",
      discriminator: [
        111,
        121,
        21,
        56,
        40,
        24,
        94,
        209
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "quote_mint",
          type: "pubkey"
        }
      ]
    },
    {
      name: "admin_cto",
      discriminator: [
        125,
        126,
        214,
        134,
        77,
        229,
        188,
        89
      ],
      accounts: [
        {
          name: "admin_set_creator_authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "mint"
        },
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "current_creator",
          docs: [
            "Not declared writable: a pre-creator (legacy) curve stores the zero key, which is the",
            "system program, whose write lock the runtime always demotes. Callers MUST still pass this",
            "account as writable whenever it is a wallet, so the outgoing creator can be paid from its",
            "vaults; otherwise the instruction fails with `CtoCreatorAccountNotWritable`. A creator that",
            "is not a system-owned wallet (a program, a sysvar, a pump-fees or other program-owned",
            "account) is skipped, its vault balances stay collectable, and it may be passed read-only."
          ]
        },
        {
          name: "current_creator_quote_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "current_creator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "current_creator"
              }
            ]
          }
        },
        {
          name: "creator_vault_quote_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "holder_creator_vault",
          docs: [
            '`["creator-vault", find_program_address(["holder-rewards", mint], pump)]`. The sweep',
            "destination on the holder path of a fee-shared coin, ignored otherwise. Re-derived in the",
            "handler before it is written to; kept out of the seeds constraints to stay under the sBPF",
            "stack frame."
          ],
          writable: true
        },
        {
          name: "holder_creator_vault_quote_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "holder_creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pump_amm",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "amm_global_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "pool_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "pool",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108
                ]
              },
              {
                kind: "const",
                value: [
                  0,
                  0
                ]
              },
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "mint"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "pump_amm_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "coin_creator_vault_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "current_creator"
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "sharing_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "account",
              path: "pump_fees"
            }
          }
        },
        {
          name: "pump_fees",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "pump_fees_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "account",
              path: "pump_fees"
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "is_holder_reward",
          type: {
            option: "bool"
          }
        },
        {
          name: "creator_fee_bps",
          type: {
            option: "u64"
          }
        },
        {
          name: "new_creator",
          type: {
            option: "pubkey"
          }
        }
      ]
    },
    {
      name: "admin_set_idl_authority",
      discriminator: [
        8,
        217,
        96,
        231,
        144,
        104,
        192,
        5
      ],
      accounts: [
        {
          name: "authority",
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "idl_account",
          writable: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "program_signer",
          pda: {
            seeds: []
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "idl_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "admin_update_token_incentives",
      discriminator: [
        209,
        11,
        115,
        87,
        213,
        23,
        124,
        204
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "global_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "mint"
        },
        {
          name: "global_incentive_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "global_volume_accumulator"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "start_time",
          type: "i64"
        },
        {
          name: "end_time",
          type: "i64"
        },
        {
          name: "seconds_in_a_day",
          type: "i64"
        },
        {
          name: "day_number",
          type: "u64"
        },
        {
          name: "pump_token_supply_per_day",
          type: "u64"
        }
      ]
    },
    {
      name: "buy",
      docs: [
        "Buys tokens from a bonding curve."
      ],
      discriminator: [
        102,
        6,
        61,
        18,
        1,
        218,
        235,
        234
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "fee_recipient",
          writable: true
        },
        {
          name: "mint"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "associated_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_user",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program"
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  1,
                  86,
                  224,
                  246,
                  147,
                  102,
                  90,
                  207,
                  68,
                  219,
                  21,
                  104,
                  191,
                  23,
                  91,
                  170,
                  81,
                  137,
                  203,
                  151,
                  245,
                  210,
                  255,
                  59,
                  101,
                  93,
                  43,
                  182,
                  253,
                  109,
                  24,
                  176
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "amount",
          type: "u64"
        },
        {
          name: "max_sol_cost",
          type: "u64"
        },
        {
          name: "track_volume",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ]
    },
    {
      name: "buy_exact_quote_in_v2",
      discriminator: [
        194,
        171,
        28,
        70,
        104,
        77,
        91,
        47
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "base_mint"
        },
        {
          name: "quote_mint"
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "fee_recipient",
          writable: true
        },
        {
          name: "associated_quote_fee_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "buyback_fee_recipient",
          writable: true
        },
        {
          name: "associated_quote_buyback_fee_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "buyback_fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ]
          }
        },
        {
          name: "associated_base_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_quote_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "associated_base_user",
          writable: true
        },
        {
          name: "associated_quote_user",
          docs: [
            "canonical SPL associated-token PDA. Validated in handlers via",
            "`validate_user_quote_token_account` for non-legacy mints; ignored for legacy (SOL) trades."
          ],
          writable: true
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "associated_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "sharing_config",
          docs: [
            "seeds; the account is intentionally not deserialized here because it may be uninitialized",
            "for mints that have not created a fee sharing config. Handlers must check",
            "`data_is_empty()` / owner before reading."
          ],
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "associated_user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user_volume_accumulator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  1,
                  86,
                  224,
                  246,
                  147,
                  102,
                  90,
                  207,
                  68,
                  219,
                  21,
                  104,
                  191,
                  23,
                  91,
                  170,
                  81,
                  137,
                  203,
                  151,
                  245,
                  210,
                  255,
                  59,
                  101,
                  93,
                  43,
                  182,
                  253,
                  109,
                  24,
                  176
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        }
      ],
      args: [
        {
          name: "spendable_quote_in",
          type: "u64"
        },
        {
          name: "min_tokens_out",
          type: "u64"
        }
      ]
    },
    {
      name: "buy_exact_sol_in",
      docs: [
        "Given a budget of spendable SOL, buy at least min_tokens_out tokens.",
        "Fees are deducted from spendable_sol_in.",
        "",
        "# Quote formulas",
        "Where:",
        "- total_fee_bps = protocol_fee_bps + creator_fee_bps (creator_fee_bps is 0 if no creator)",
        "- floor(a/b) = a / b (integer division)",
        "- ceil(a/b) = (a + b - 1) / b",
        "",
        "SOL \u2192 tokens quote",
        "To calculate tokens_out for a given spendable_sol_in:",
        "1. net_sol = floor(spendable_sol_in * 10_000 / (10_000 + total_fee_bps))",
        "2. fees = ceil(net_sol * protocol_fee_bps / 10_000) + ceil(net_sol * creator_fee_bps / 10_000) (creator_fee_bps is 0 if no creator)",
        "3. if net_sol + fees > spendable_sol_in: net_sol = net_sol - (net_sol + fees - spendable_sol_in)",
        "4. tokens_out = floor((net_sol - 1) * virtual_token_reserves / (virtual_sol_reserves + net_sol - 1))",
        "",
        "Reverse quote (tokens \u2192 SOL)",
        "To calculate spendable_sol_in for a desired number of tokens:",
        "1. net_sol = ceil(tokens * virtual_sol_reserves / (virtual_token_reserves - tokens)) + 1",
        "2. spendable_sol_in = ceil(net_sol * (10_000 + total_fee_bps) / 10_000)",
        "",
        "Rent",
        "Separately make sure the instruction's payer has enough SOL to cover rent for:",
        "- creator_vault: rent.minimum_balance(0)",
        "- user_volume_accumulator: rent.minimum_balance(UserVolumeAccumulator::LEN)"
      ],
      discriminator: [
        56,
        252,
        116,
        8,
        158,
        223,
        205,
        95
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "fee_recipient",
          writable: true
        },
        {
          name: "mint"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "associated_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_user",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program"
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  1,
                  86,
                  224,
                  246,
                  147,
                  102,
                  90,
                  207,
                  68,
                  219,
                  21,
                  104,
                  191,
                  23,
                  91,
                  170,
                  81,
                  137,
                  203,
                  151,
                  245,
                  210,
                  255,
                  59,
                  101,
                  93,
                  43,
                  182,
                  253,
                  109,
                  24,
                  176
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "spendable_sol_in",
          type: "u64"
        },
        {
          name: "min_tokens_out",
          type: "u64"
        },
        {
          name: "track_volume",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ]
    },
    {
      name: "buy_v2",
      discriminator: [
        184,
        23,
        238,
        97,
        103,
        197,
        211,
        61
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "base_mint"
        },
        {
          name: "quote_mint"
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "fee_recipient",
          writable: true
        },
        {
          name: "associated_quote_fee_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "buyback_fee_recipient",
          writable: true
        },
        {
          name: "associated_quote_buyback_fee_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "buyback_fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ]
          }
        },
        {
          name: "associated_base_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_quote_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "associated_base_user",
          writable: true
        },
        {
          name: "associated_quote_user",
          docs: [
            "canonical SPL associated-token PDA. Validated in handlers via",
            "`validate_user_quote_token_account` for non-legacy mints; ignored for legacy (SOL) trades."
          ],
          writable: true
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "associated_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "sharing_config",
          docs: [
            "seeds; the account is intentionally not deserialized here because it may be uninitialized",
            "for mints that have not created a fee sharing config. Handlers must check",
            "`data_is_empty()` / owner before reading."
          ],
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "associated_user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user_volume_accumulator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  1,
                  86,
                  224,
                  246,
                  147,
                  102,
                  90,
                  207,
                  68,
                  219,
                  21,
                  104,
                  191,
                  23,
                  91,
                  170,
                  81,
                  137,
                  203,
                  151,
                  245,
                  210,
                  255,
                  59,
                  101,
                  93,
                  43,
                  182,
                  253,
                  109,
                  24,
                  176
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        }
      ],
      args: [
        {
          name: "amount",
          type: "u64"
        },
        {
          name: "max_sol_cost",
          type: "u64"
        }
      ]
    },
    {
      name: "claim_cashback",
      discriminator: [
        37,
        58,
        35,
        126,
        190,
        53,
        228,
        197
      ],
      accounts: [
        {
          name: "user",
          writable: true
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        }
      ],
      args: []
    },
    {
      name: "claim_cashback_v2",
      docs: [
        "Pays out the user's accrued cashback. For a token quote, `associated_quote_user` may be",
        "any token account of `quote_mint` owned by `user`, not only the associated one."
      ],
      discriminator: [
        122,
        243,
        204,
        65,
        94,
        116,
        29,
        55
      ],
      accounts: [
        {
          name: "user",
          writable: true
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "associated_user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user_volume_accumulator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "associated_quote_user",
          writable: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        }
      ],
      args: []
    },
    {
      name: "claim_token_incentives",
      discriminator: [
        16,
        4,
        71,
        28,
        204,
        1,
        40,
        27
      ],
      accounts: [
        {
          name: "user"
        },
        {
          name: "user_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "global_incentive_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "global_volume_accumulator"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "mint",
          relations: [
            "global_volume_accumulator"
          ]
        },
        {
          name: "token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "payer",
          writable: true,
          signer: true
        }
      ],
      args: []
    },
    {
      name: "close_user_volume_accumulator",
      discriminator: [
        249,
        69,
        164,
        218,
        150,
        103,
        84,
        138
      ],
      accounts: [
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "collect_creator_fee",
      docs: [
        "Collects creator_fee from creator_vault to the coin creator account"
      ],
      discriminator: [
        20,
        22,
        86,
        123,
        198,
        28,
        219,
        132
      ],
      accounts: [
        {
          name: "creator",
          writable: true
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "creator"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "collect_creator_fee_v2",
      docs: [
        "Collects creator_fee from creator_vault to the coin creator account"
      ],
      discriminator: [
        207,
        17,
        138,
        242,
        4,
        34,
        19,
        56
      ],
      accounts: [
        {
          name: "creator",
          writable: true
        },
        {
          name: "creator_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "creator"
              }
            ]
          }
        },
        {
          name: "creator_vault_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "create",
      docs: [
        "Creates a new coin and bonding curve."
      ],
      discriminator: [
        24,
        30,
        200,
        40,
        5,
        28,
        7,
        119
      ],
      accounts: [
        {
          name: "mint",
          writable: true,
          signer: true
        },
        {
          name: "mint_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  105,
                  110,
                  116,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "associated_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "const",
                value: [
                  6,
                  221,
                  246,
                  225,
                  215,
                  101,
                  161,
                  147,
                  217,
                  203,
                  225,
                  70,
                  206,
                  235,
                  121,
                  172,
                  28,
                  180,
                  133,
                  237,
                  95,
                  91,
                  55,
                  145,
                  58,
                  140,
                  245,
                  133,
                  126,
                  255,
                  0,
                  169
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "mpl_token_metadata",
          address: "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        },
        {
          name: "metadata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  101,
                  116,
                  97,
                  100,
                  97,
                  116,
                  97
                ]
              },
              {
                kind: "const",
                value: [
                  11,
                  112,
                  101,
                  177,
                  227,
                  209,
                  124,
                  69,
                  56,
                  157,
                  82,
                  127,
                  107,
                  4,
                  195,
                  205,
                  88,
                  184,
                  108,
                  115,
                  26,
                  160,
                  253,
                  181,
                  73,
                  182,
                  209,
                  188,
                  3,
                  248,
                  41,
                  70
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "account",
              path: "mpl_token_metadata"
            }
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program",
          address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "rent",
          address: "SysvarRent111111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "name",
          type: "string"
        },
        {
          name: "symbol",
          type: "string"
        },
        {
          name: "uri",
          type: "string"
        },
        {
          name: "creator",
          type: "pubkey"
        }
      ]
    },
    {
      name: "create_v2",
      docs: [
        "Creates a new spl-22 coin and bonding curve.",
        "",
        "Remaining accounts select the quote mint (none = SOL): `quote_mint`,",
        "`associated_quote_bonding_curve`, `quote_token_program` (SPL Token or Token-2022; must own",
        "the mint), plus an optional fourth account, the `quote-control` PDA, read only when `Global`",
        "does not whitelist the mint. A mint admitted through quote-control seeds the curve's",
        "virtual quote reserves from its quote-control entry instead of `Global`, and cannot be",
        "used with `is_mayhem_mode` (`MayhemModeQuoteMintNotAllowed`). The Token-2022",
        "native mint is rejected, and a Token-2022 quote mint may only carry the xStock operable",
        "extension set (metadata pointer/metadata, permanent delegate, initialized default account",
        "state, scaled UI amount, pausable, confidential-transfer mint, and a transfer hook with no",
        "program). The trailing `creator_fee_bps` argument (EOF-tolerant) sets the coin's own creator",
        "fee rate for a quote mint admitted through quote-control, and then requires",
        "`Global.creator_fee_configurable`, a non-cashback coin and a value in",
        "`1..=Global.max_configurable_creator_fee_bps`; on a SOL or `Global`-whitelisted quote it is",
        "ignored, and omitted or zero stores 0 so the pump-fees schedule rate applies.",
        "`is_cashback_enabled` is deprecated and must be false. `is_holder_reward` (EOF-tolerant,",
        "gated by `Global.is_holder_reward_enabled`) sets the creator to the `holder-rewards` PDA",
        "of the mint, so creator fees accrue to its creator vault, are collected onto the PDA with",
        "`collect_creator_fee*` and paid out through `distribute_fee_to_holders`."
      ],
      discriminator: [
        214,
        144,
        76,
        236,
        95,
        139,
        49,
        180
      ],
      accounts: [
        {
          name: "mint",
          writable: true,
          signer: true
        },
        {
          name: "mint_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  105,
                  110,
                  116,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "associated_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "mayhem_program_id",
          writable: true,
          address: "MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e"
        },
        {
          name: "global_params",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  45,
                  112,
                  97,
                  114,
                  97,
                  109,
                  115
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                5,
                42,
                229,
                215,
                167,
                218,
                167,
                36,
                166,
                234,
                176,
                167,
                41,
                84,
                145,
                133,
                90,
                212,
                160,
                103,
                22,
                96,
                103,
                76,
                78,
                3,
                69,
                89,
                128,
                61,
                101,
                163
              ]
            }
          }
        },
        {
          name: "sol_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  111,
                  108,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                5,
                42,
                229,
                215,
                167,
                218,
                167,
                36,
                166,
                234,
                176,
                167,
                41,
                84,
                145,
                133,
                90,
                212,
                160,
                103,
                22,
                96,
                103,
                76,
                78,
                3,
                69,
                89,
                128,
                61,
                101,
                163
              ]
            }
          }
        },
        {
          name: "mayhem_state",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  97,
                  121,
                  104,
                  101,
                  109,
                  45,
                  115,
                  116,
                  97,
                  116,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                5,
                42,
                229,
                215,
                167,
                218,
                167,
                36,
                166,
                234,
                176,
                167,
                41,
                84,
                145,
                133,
                90,
                212,
                160,
                103,
                22,
                96,
                103,
                76,
                78,
                3,
                69,
                89,
                128,
                61,
                101,
                163
              ]
            }
          }
        },
        {
          name: "mayhem_token_vault",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "name",
          type: "string"
        },
        {
          name: "symbol",
          type: "string"
        },
        {
          name: "uri",
          type: "string"
        },
        {
          name: "creator",
          type: "pubkey"
        },
        {
          name: "is_mayhem_mode",
          type: "bool"
        },
        {
          name: "is_cashback_enabled",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        },
        {
          name: "creator_fee_bps",
          type: {
            defined: {
              name: "OptionU64"
            }
          }
        },
        {
          name: "is_holder_reward",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ]
    },
    {
      name: "distribute_creator_fees",
      docs: [
        "Distributes creator fees to shareholders based on their share percentages",
        "The creator vault needs to have at least the minimum distributable amount to distribute fees",
        "This can be checked with the get_minimum_distributable_fee instruction"
      ],
      discriminator: [
        165,
        114,
        103,
        0,
        121,
        206,
        247,
        81
      ],
      accounts: [
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "sharing_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        }
      ],
      args: [],
      returns: {
        defined: {
          name: "DistributeCreatorFeesEvent"
        }
      }
    },
    {
      name: "distribute_creator_fees_v2",
      discriminator: [
        255,
        203,
        19,
        79,
        244,
        68,
        8,
        159
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "sharing_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "creator_vault_quote_token_account",
          docs: [
            "Deserialized manually in the handler for non-legacy quote mints."
          ],
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        }
      ],
      args: [
        {
          name: "initialize_ata",
          type: "bool"
        }
      ],
      returns: {
        defined: {
          name: "DistributeCreatorFeesEvent"
        }
      }
    },
    {
      name: "distribute_fee_to_holders",
      docs: [
        "Pays fees collected on the `holder-rewards` PDA (via `collect_creator_fee*` with the PDA",
        "as creator) out to holders: `amounts[i]` goes to remaining accounts `[2i]` (owner) /",
        "`[2i + 1]` (its quote ATA, created if missing). `holder_rewards_token_account` is any",
        "quote token account owned by the PDA (normally its ATA): the source on a token quote, and",
        "on a SOL quote a parked WSOL account closed into the PDA first; pass the program id when",
        "there is none. Signed by `Global.holder_reward_claim_authority`."
      ],
      discriminator: [
        98,
        54,
        145,
        97,
        2,
        70,
        173,
        43
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "holder_reward_claim_authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "mint"
        },
        {
          name: "holder_rewards",
          docs: [
            "deliver the collected fees here (lamports on a SOL quote)"
          ],
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  104,
                  111,
                  108,
                  100,
                  101,
                  114,
                  45,
                  114,
                  101,
                  119,
                  97,
                  114,
                  100,
                  115
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "holder_rewards_token_account",
          writable: true,
          optional: true
        },
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "amounts",
          type: {
            vec: "u64"
          }
        }
      ]
    },
    {
      name: "extend_account",
      docs: [
        "Extends the size of program-owned accounts"
      ],
      discriminator: [
        234,
        102,
        194,
        203,
        150,
        72,
        62,
        229
      ],
      accounts: [
        {
          name: "account",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "get_minimum_distributable_fee",
      docs: [
        "Permissionless instruction to check the minimum required fees for distribution",
        "Returns the minimum required balance from the creator_vault and whether distribution can proceed"
      ],
      discriminator: [
        117,
        225,
        127,
        202,
        134,
        95,
        68,
        35
      ],
      accounts: [
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "sharing_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "creator_vault",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        }
      ],
      args: [],
      returns: {
        defined: {
          name: "MinimumDistributableFeeEvent"
        }
      }
    },
    {
      name: "init_user_volume_accumulator",
      discriminator: [
        94,
        6,
        202,
        115,
        255,
        96,
        232,
        183
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "user"
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "initialize",
      docs: [
        "Creates the global state."
      ],
      discriminator: [
        175,
        175,
        109,
        31,
        13,
        152,
        155,
        237
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        }
      ],
      args: []
    },
    {
      name: "initialize_quote_control",
      discriminator: [
        239,
        73,
        245,
        173,
        209,
        177,
        84,
        66
      ],
      accounts: [
        {
          name: "quote_control",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  113,
                  117,
                  111,
                  116,
                  101,
                  45,
                  99,
                  111,
                  110,
                  116,
                  114,
                  111,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        }
      ],
      args: []
    },
    {
      name: "migrate",
      docs: [
        "Migrates liquidity to pump_amm if the bonding curve is complete"
      ],
      discriminator: [
        155,
        234,
        231,
        146,
        236,
        158,
        162,
        30
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "withdraw_authority",
          writable: true,
          relations: [
            "global"
          ]
        },
        {
          name: "mint"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "associated_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "mint"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program",
          address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        },
        {
          name: "pump_amm",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "pool",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108
                ]
              },
              {
                kind: "const",
                value: [
                  0,
                  0
                ]
              },
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "mint"
              },
              {
                kind: "account",
                path: "wsol_mint"
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "pool_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "pool_authority_mint_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "mint"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pool_authority_wsol_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "wsol_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "amm_global_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "wsol_mint",
          address: "So11111111111111111111111111111111111111112"
        },
        {
          name: "lp_mint",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  95,
                  108,
                  112,
                  95,
                  109,
                  105,
                  110,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool"
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "user_pool_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "token_2022_program"
              },
              {
                kind: "account",
                path: "lp_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pool_base_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool"
              },
              {
                kind: "account",
                path: "mint"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "wsol_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "token_2022_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "pump_amm_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "rent",
          address: "SysvarRent111111111111111111111111111111111"
        }
      ],
      args: []
    },
    {
      name: "migrate_bonding_curve_creator",
      discriminator: [
        87,
        124,
        52,
        191,
        52,
        38,
        214,
        232
      ],
      accounts: [
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "sharing_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "migrate_v2",
      docs: [
        "Migrates liquidity to pump_amm if the bonding curve is complete"
      ],
      discriminator: [
        187,
        203,
        18,
        31,
        206,
        237,
        254,
        41
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "withdraw_authority",
          writable: true,
          relations: [
            "global"
          ]
        },
        {
          name: "base_mint"
        },
        {
          name: "quote_mint"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ]
          }
        },
        {
          name: "associated_base_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_quote_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "pump_amm",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "pool",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108
                ]
              },
              {
                kind: "const",
                value: [
                  0,
                  0
                ]
              },
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "base_mint"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "pool_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ]
          }
        },
        {
          name: "pool_authority_mint_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pool_authority_quote_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "amm_global_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "lp_mint",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  95,
                  108,
                  112,
                  95,
                  109,
                  105,
                  110,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool"
              }
            ],
            program: {
              kind: "account",
              path: "pump_amm"
            }
          }
        },
        {
          name: "user_pool_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool_authority"
              },
              {
                kind: "account",
                path: "token_2022_program"
              },
              {
                kind: "account",
                path: "lp_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pool_base_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "token_2022_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "pump_amm_event_authority"
        },
        {
          name: "rent",
          address: "SysvarRent111111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "remove_quote_control_mint",
      discriminator: [
        223,
        7,
        253,
        26,
        81,
        165,
        218,
        166
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "quote_control",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  113,
                  117,
                  111,
                  116,
                  101,
                  45,
                  99,
                  111,
                  110,
                  116,
                  114,
                  111,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "quote_mint",
          type: "pubkey"
        }
      ]
    },
    {
      name: "remove_quote_mint",
      discriminator: [
        177,
        65,
        223,
        38,
        88,
        209,
        158,
        155
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "quote_mint",
          type: "pubkey"
        }
      ]
    },
    {
      name: "sell",
      docs: [
        "Sells tokens into a bonding curve.",
        "For cashback coins, pass as remaining_accounts: [0] user_volume_accumulator,",
        "[1] bonding_curve_v2. If provided and valid, creator_fee goes to user_volume_accumulator.",
        "Otherwise, falls back to transferring creator_fee to creator_vault."
      ],
      discriminator: [
        51,
        230,
        133,
        164,
        1,
        127,
        131,
        173
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "fee_recipient",
          writable: true
        },
        {
          name: "mint"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "associated_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_user",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "token_program"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  1,
                  86,
                  224,
                  246,
                  147,
                  102,
                  90,
                  207,
                  68,
                  219,
                  21,
                  104,
                  191,
                  23,
                  91,
                  170,
                  81,
                  137,
                  203,
                  151,
                  245,
                  210,
                  255,
                  59,
                  101,
                  93,
                  43,
                  182,
                  253,
                  109,
                  24,
                  176
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "amount",
          type: "u64"
        },
        {
          name: "min_sol_output",
          type: "u64"
        }
      ]
    },
    {
      name: "sell_v2",
      discriminator: [
        93,
        246,
        130,
        60,
        231,
        233,
        64,
        178
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "base_mint"
        },
        {
          name: "quote_mint"
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "fee_recipient",
          writable: true
        },
        {
          name: "associated_quote_fee_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "buyback_fee_recipient",
          writable: true
        },
        {
          name: "associated_quote_buyback_fee_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "buyback_fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ]
          }
        },
        {
          name: "associated_base_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_quote_bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "bonding_curve"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "associated_base_user",
          writable: true
        },
        {
          name: "associated_quote_user",
          docs: [
            "canonical SPL associated-token PDA. Validated in `sell_v2_ix` via",
            "`validate_user_quote_token_account` for non-legacy mints; ignored for legacy (SOL) trades."
          ],
          writable: true
        },
        {
          name: "creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "bonding_curve.creator",
                account: "BondingCurve"
              }
            ]
          }
        },
        {
          name: "associated_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator_vault"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "sharing_config",
          docs: [
            "seeds; the account is intentionally not deserialized here because it may be uninitialized",
            "for mints that have not created a fee sharing config. Handlers must check",
            "`data_is_empty()` / owner before reading."
          ],
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "associated_user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user_volume_accumulator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  1,
                  86,
                  224,
                  246,
                  147,
                  102,
                  90,
                  207,
                  68,
                  219,
                  21,
                  104,
                  191,
                  23,
                  91,
                  170,
                  81,
                  137,
                  203,
                  151,
                  245,
                  210,
                  255,
                  59,
                  101,
                  93,
                  43,
                  182,
                  253,
                  109,
                  24,
                  176
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        }
      ],
      args: [
        {
          name: "amount",
          type: "u64"
        },
        {
          name: "min_sol_output",
          type: "u64"
        }
      ]
    },
    {
      name: "set_creator",
      docs: [
        "Allows Global::set_creator_authority to set the bonding curve creator from Metaplex metadata or input argument"
      ],
      discriminator: [
        254,
        148,
        255,
        112,
        207,
        142,
        170,
        165
      ],
      accounts: [
        {
          name: "set_creator_authority",
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "mint"
        },
        {
          name: "metadata",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  101,
                  116,
                  97,
                  100,
                  97,
                  116,
                  97
                ]
              },
              {
                kind: "const",
                value: [
                  11,
                  112,
                  101,
                  177,
                  227,
                  209,
                  124,
                  69,
                  56,
                  157,
                  82,
                  127,
                  107,
                  4,
                  195,
                  205,
                  88,
                  184,
                  108,
                  115,
                  26,
                  160,
                  253,
                  181,
                  73,
                  182,
                  209,
                  188,
                  3,
                  248,
                  41,
                  70
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                11,
                112,
                101,
                177,
                227,
                209,
                124,
                69,
                56,
                157,
                82,
                127,
                107,
                4,
                195,
                205,
                88,
                184,
                108,
                115,
                26,
                160,
                253,
                181,
                73,
                182,
                209,
                188,
                3,
                248,
                41,
                70
              ]
            }
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "creator",
          type: "pubkey"
        }
      ]
    },
    {
      name: "set_mayhem_virtual_params",
      discriminator: [
        61,
        169,
        188,
        191,
        153,
        149,
        42,
        97
      ],
      accounts: [
        {
          name: "sol_vault_authority",
          writable: true,
          signer: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  111,
                  108,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                5,
                42,
                229,
                215,
                167,
                218,
                167,
                36,
                166,
                234,
                176,
                167,
                41,
                84,
                145,
                133,
                90,
                212,
                160,
                103,
                22,
                96,
                103,
                76,
                78,
                3,
                69,
                89,
                128,
                61,
                101,
                163
              ]
            }
          }
        },
        {
          name: "mayhem_token_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "sol_vault_authority"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "mint"
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "token_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "set_metaplex_creator",
      docs: [
        "Syncs the bonding curve creator with the Metaplex metadata creator if it exists"
      ],
      discriminator: [
        138,
        96,
        174,
        217,
        48,
        85,
        197,
        246
      ],
      accounts: [
        {
          name: "mint"
        },
        {
          name: "metadata",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  101,
                  116,
                  97,
                  100,
                  97,
                  116,
                  97
                ]
              },
              {
                kind: "const",
                value: [
                  11,
                  112,
                  101,
                  177,
                  227,
                  209,
                  124,
                  69,
                  56,
                  157,
                  82,
                  127,
                  107,
                  4,
                  195,
                  205,
                  88,
                  184,
                  108,
                  115,
                  26,
                  160,
                  253,
                  181,
                  73,
                  182,
                  209,
                  188,
                  3,
                  248,
                  41,
                  70
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                11,
                112,
                101,
                177,
                227,
                209,
                124,
                69,
                56,
                157,
                82,
                127,
                107,
                4,
                195,
                205,
                88,
                184,
                108,
                115,
                26,
                160,
                253,
                181,
                73,
                182,
                209,
                188,
                3,
                248,
                41,
                70
              ]
            }
          }
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "set_params",
      docs: [
        "Sets the global state parameters."
      ],
      discriminator: [
        27,
        234,
        178,
        52,
        147,
        2,
        187,
        141
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "initial_virtual_token_reserves",
          type: "u64"
        },
        {
          name: "initial_virtual_sol_reserves",
          type: "u64"
        },
        {
          name: "initial_real_token_reserves",
          type: "u64"
        },
        {
          name: "token_total_supply",
          type: "u64"
        },
        {
          name: "fee_basis_points",
          type: "u64"
        },
        {
          name: "withdraw_authority",
          type: "pubkey"
        },
        {
          name: "enable_migrate",
          type: "bool"
        },
        {
          name: "pool_migration_fee",
          type: "u64"
        },
        {
          name: "creator_fee_basis_points",
          type: "u64"
        },
        {
          name: "set_creator_authority",
          type: "pubkey"
        },
        {
          name: "admin_set_creator_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "set_quote_control_admin",
      discriminator: [
        62,
        79,
        161,
        211,
        165,
        170,
        214,
        210
      ],
      accounts: [
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "quote_control",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  113,
                  117,
                  111,
                  116,
                  101,
                  45,
                  99,
                  111,
                  110,
                  116,
                  114,
                  111,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "new_admin",
          type: "pubkey"
        }
      ]
    },
    {
      name: "set_reserved_fee_recipients",
      discriminator: [
        111,
        172,
        162,
        232,
        114,
        89,
        213,
        142
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "whitelist_pda",
          type: "pubkey"
        }
      ]
    },
    {
      name: "set_virtual_quote_reserves",
      discriminator: [
        101,
        135,
        191,
        104,
        9,
        88,
        20,
        96
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "initial_virtual_quote_reserves",
          type: "u64"
        }
      ]
    },
    {
      name: "sync_user_volume_accumulator",
      discriminator: [
        86,
        31,
        192,
        87,
        163,
        87,
        79,
        238
      ],
      accounts: [
        {
          name: "user"
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "toggle_cashback_enabled",
      discriminator: [
        115,
        103,
        224,
        255,
        189,
        89,
        86,
        195
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "enabled",
          type: "bool"
        }
      ]
    },
    {
      name: "toggle_create_v2",
      discriminator: [
        28,
        255,
        230,
        240,
        172,
        107,
        203,
        171
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "enabled",
          type: "bool"
        }
      ]
    },
    {
      name: "toggle_mayhem_mode",
      discriminator: [
        1,
        9,
        111,
        208,
        100,
        31,
        255,
        163
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "enabled",
          type: "bool"
        }
      ]
    },
    {
      name: "update_buyback_config",
      discriminator: [
        251,
        224,
        171,
        146,
        160,
        26,
        113,
        233
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "buyback_basis_points",
          type: {
            option: "u64"
          }
        }
      ]
    },
    {
      name: "update_creator_fee_config",
      discriminator: [
        61,
        175,
        160,
        249,
        66,
        66,
        136,
        175
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "creator_fee_configurable",
          type: "bool"
        },
        {
          name: "max_configurable_creator_fee_bps",
          type: "u64"
        }
      ]
    },
    {
      name: "update_global_authority",
      discriminator: [
        227,
        181,
        74,
        196,
        208,
        21,
        97,
        213
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "new_authority"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "update_holder_reward_config",
      discriminator: [
        225,
        252,
        66,
        4,
        199,
        35,
        236,
        16
      ],
      accounts: [
        {
          name: "global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "is_holder_reward_enabled",
          type: "bool"
        },
        {
          name: "holder_reward_claim_authority",
          type: "pubkey"
        }
      ]
    }
  ],
  accounts: [
    {
      name: "BondingCurve",
      discriminator: [
        23,
        183,
        248,
        55,
        96,
        216,
        172,
        96
      ]
    },
    {
      name: "FeeConfig",
      discriminator: [
        143,
        52,
        146,
        187,
        219,
        123,
        76,
        155
      ]
    },
    {
      name: "Global",
      discriminator: [
        167,
        232,
        232,
        177,
        200,
        108,
        114,
        127
      ]
    },
    {
      name: "GlobalVolumeAccumulator",
      discriminator: [
        202,
        42,
        246,
        43,
        142,
        190,
        30,
        255
      ]
    },
    {
      name: "QuoteControl",
      discriminator: [
        56,
        244,
        35,
        238,
        193,
        213,
        162,
        201
      ]
    },
    {
      name: "SharingConfig",
      discriminator: [
        216,
        74,
        9,
        0,
        56,
        140,
        93,
        75
      ]
    },
    {
      name: "UserVolumeAccumulator",
      discriminator: [
        86,
        255,
        112,
        14,
        102,
        53,
        154,
        250
      ]
    }
  ],
  events: [
    {
      name: "AddQuoteControlMintEvent",
      discriminator: [
        164,
        175,
        87,
        74,
        88,
        45,
        33,
        62
      ]
    },
    {
      name: "AdminCtoEvent",
      discriminator: [
        110,
        124,
        226,
        98,
        170,
        255,
        17,
        120
      ]
    },
    {
      name: "AdminSetIdlAuthorityEvent",
      discriminator: [
        245,
        59,
        70,
        34,
        75,
        185,
        109,
        92
      ]
    },
    {
      name: "AdminUpdateTokenIncentivesEvent",
      discriminator: [
        147,
        250,
        108,
        120,
        247,
        29,
        67,
        222
      ]
    },
    {
      name: "ClaimCashbackEvent",
      discriminator: [
        226,
        214,
        246,
        33,
        7,
        242,
        147,
        229
      ]
    },
    {
      name: "ClaimTokenIncentivesEvent",
      discriminator: [
        79,
        172,
        246,
        49,
        205,
        91,
        206,
        232
      ]
    },
    {
      name: "CloseUserVolumeAccumulatorEvent",
      discriminator: [
        146,
        159,
        189,
        172,
        146,
        88,
        56,
        244
      ]
    },
    {
      name: "CollectCreatorFeeEvent",
      discriminator: [
        122,
        2,
        127,
        1,
        14,
        191,
        12,
        175
      ]
    },
    {
      name: "CompleteEvent",
      discriminator: [
        95,
        114,
        97,
        156,
        212,
        46,
        152,
        8
      ]
    },
    {
      name: "CompletePumpAmmMigrationEvent",
      discriminator: [
        189,
        233,
        93,
        185,
        92,
        148,
        234,
        148
      ]
    },
    {
      name: "CreateEvent",
      discriminator: [
        27,
        114,
        169,
        77,
        222,
        235,
        99,
        118
      ]
    },
    {
      name: "DistributeCreatorFeesEvent",
      discriminator: [
        165,
        55,
        129,
        112,
        4,
        179,
        202,
        40
      ]
    },
    {
      name: "DistributeFeeToHoldersEvent",
      discriminator: [
        227,
        190,
        215,
        206,
        176,
        180,
        165,
        132
      ]
    },
    {
      name: "ExtendAccountEvent",
      discriminator: [
        97,
        97,
        215,
        144,
        93,
        146,
        22,
        124
      ]
    },
    {
      name: "InitUserVolumeAccumulatorEvent",
      discriminator: [
        134,
        36,
        13,
        72,
        232,
        101,
        130,
        216
      ]
    },
    {
      name: "MigrateBondingCurveCreatorEvent",
      discriminator: [
        155,
        167,
        104,
        220,
        213,
        108,
        243,
        3
      ]
    },
    {
      name: "MinimumDistributableFeeEvent",
      discriminator: [
        168,
        216,
        132,
        239,
        235,
        182,
        49,
        52
      ]
    },
    {
      name: "RemoveQuoteControlMintEvent",
      discriminator: [
        46,
        33,
        86,
        134,
        0,
        213,
        209,
        48
      ]
    },
    {
      name: "ReservedFeeRecipientsEvent",
      discriminator: [
        43,
        188,
        250,
        18,
        221,
        75,
        187,
        95
      ]
    },
    {
      name: "SetCreatorEvent",
      discriminator: [
        237,
        52,
        123,
        37,
        245,
        251,
        72,
        210
      ]
    },
    {
      name: "SetMetaplexCreatorEvent",
      discriminator: [
        142,
        203,
        6,
        32,
        127,
        105,
        191,
        162
      ]
    },
    {
      name: "SetParamsEvent",
      discriminator: [
        223,
        195,
        159,
        246,
        62,
        48,
        143,
        131
      ]
    },
    {
      name: "SetQuoteControlAdminEvent",
      discriminator: [
        74,
        248,
        141,
        69,
        202,
        81,
        30,
        247
      ]
    },
    {
      name: "SyncUserVolumeAccumulatorEvent",
      discriminator: [
        197,
        122,
        167,
        124,
        116,
        81,
        91,
        255
      ]
    },
    {
      name: "TradeEvent",
      discriminator: [
        189,
        219,
        127,
        211,
        78,
        230,
        97,
        238
      ]
    },
    {
      name: "UpdateCreatorFeeConfigEvent",
      discriminator: [
        152,
        198,
        124,
        124,
        106,
        246,
        127,
        191
      ]
    },
    {
      name: "UpdateGlobalAuthorityEvent",
      discriminator: [
        182,
        195,
        137,
        42,
        35,
        206,
        207,
        247
      ]
    },
    {
      name: "UpdateMayhemVirtualParamsEvent",
      discriminator: [
        117,
        123,
        228,
        182,
        161,
        168,
        220,
        214
      ]
    }
  ],
  errors: [
    {
      code: 6e3,
      name: "NotAuthorized",
      msg: "The given account is not authorized to execute this instruction."
    },
    {
      code: 6001,
      name: "AlreadyInitialized",
      msg: "The program is already initialized."
    },
    {
      code: 6002,
      name: "TooMuchSolRequired",
      msg: "slippage: Too much SOL required to buy the given amount of tokens."
    },
    {
      code: 6003,
      name: "TooLittleSolReceived",
      msg: "slippage: Too little SOL received to sell the given amount of tokens."
    },
    {
      code: 6004,
      name: "MintDoesNotMatchBondingCurve",
      msg: "The mint does not match the bonding curve."
    },
    {
      code: 6005,
      name: "BondingCurveComplete",
      msg: "The bonding curve has completed and liquidity migrated to raydium."
    },
    {
      code: 6006,
      name: "BondingCurveNotComplete",
      msg: "The bonding curve has not completed."
    },
    {
      code: 6007,
      name: "NotInitialized",
      msg: "The program is not initialized."
    },
    {
      code: 6008,
      name: "WithdrawTooFrequent",
      msg: "Withdraw too frequent"
    },
    {
      code: 6009,
      name: "NewSizeShouldBeGreaterThanCurrentSize",
      msg: "new_size should be > current_size"
    },
    {
      code: 6010,
      name: "AccountTypeNotSupported",
      msg: "Account type not supported"
    },
    {
      code: 6011,
      name: "InitialRealTokenReservesShouldBeLessThanTokenTotalSupply",
      msg: "initial_real_token_reserves should be less than token_total_supply"
    },
    {
      code: 6012,
      name: "InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves",
      msg: "initial_virtual_token_reserves should be greater than initial_real_token_reserves"
    },
    {
      code: 6013,
      name: "FeeBasisPointsGreaterThanMaximum",
      msg: "fee_basis_points greater than maximum"
    },
    {
      code: 6014,
      name: "AllZerosWithdrawAuthority",
      msg: "Withdraw authority cannot be set to System Program ID"
    },
    {
      code: 6015,
      name: "PoolMigrationFeeShouldBeLessThanFinalRealSolReserves",
      msg: "pool_migration_fee should be less than final_real_sol_reserves"
    },
    {
      code: 6016,
      name: "PoolMigrationFeeShouldBeGreaterThanCreatorFeePlusMaxMigrateFees",
      msg: "pool_migration_fee should be greater than creator_fee + MAX_MIGRATE_FEES"
    },
    {
      code: 6017,
      name: "DisabledWithdraw",
      msg: "Migrate instruction is disabled"
    },
    {
      code: 6018,
      name: "DisabledMigrate",
      msg: "Migrate instruction is disabled"
    },
    {
      code: 6019,
      name: "InvalidCreator",
      msg: "Invalid creator pubkey"
    },
    {
      code: 6020,
      name: "BuyZeroAmount",
      msg: "Buy zero amount"
    },
    {
      code: 6021,
      name: "NotEnoughTokensToBuy",
      msg: "Not enough tokens to buy"
    },
    {
      code: 6022,
      name: "SellZeroAmount",
      msg: "Sell zero amount"
    },
    {
      code: 6023,
      name: "NotEnoughTokensToSell",
      msg: "Not enough tokens to sell"
    },
    {
      code: 6024,
      name: "Overflow",
      msg: "Overflow"
    },
    {
      code: 6025,
      name: "Truncation",
      msg: "Truncation"
    },
    {
      code: 6026,
      name: "DivisionByZero",
      msg: "Division by zero"
    },
    {
      code: 6027,
      name: "NotEnoughRemainingAccounts",
      msg: "Not enough remaining accounts"
    },
    {
      code: 6028,
      name: "AllFeeRecipientsShouldBeNonZero",
      msg: "All fee recipients should be non-zero"
    },
    {
      code: 6029,
      name: "UnsortedNotUniqueFeeRecipients",
      msg: "Unsorted or not unique fee recipients"
    },
    {
      code: 6030,
      name: "CreatorShouldNotBeZero",
      msg: "Creator should not be zero"
    },
    {
      code: 6031,
      name: "StartTimeInThePast"
    },
    {
      code: 6032,
      name: "EndTimeInThePast"
    },
    {
      code: 6033,
      name: "EndTimeBeforeStartTime"
    },
    {
      code: 6034,
      name: "TimeRangeTooLarge"
    },
    {
      code: 6035,
      name: "EndTimeBeforeCurrentDay"
    },
    {
      code: 6036,
      name: "SupplyUpdateForFinishedRange"
    },
    {
      code: 6037,
      name: "DayIndexAfterEndIndex"
    },
    {
      code: 6038,
      name: "DayInActiveRange"
    },
    {
      code: 6039,
      name: "InvalidIncentiveMint"
    },
    {
      code: 6040,
      name: "BuyNotEnoughSolToCoverRent",
      msg: "Buy: Not enough SOL to cover for rent exemption."
    },
    {
      code: 6041,
      name: "BuyNotEnoughSolToCoverFees",
      msg: "Buy: Not enough SOL to cover for fees."
    },
    {
      code: 6042,
      name: "BuySlippageBelowMinTokensOut",
      msg: "Slippage: Would buy less tokens than expected min_tokens_out"
    },
    {
      code: 6043,
      name: "NameTooLong"
    },
    {
      code: 6044,
      name: "SymbolTooLong"
    },
    {
      code: 6045,
      name: "UriTooLong"
    },
    {
      code: 6046,
      name: "CreateV2Disabled"
    },
    {
      code: 6047,
      name: "CpitializeMayhemFailed"
    },
    {
      code: 6048,
      name: "MayhemModeDisabled"
    },
    {
      code: 6049,
      name: "CreatorMigratedToSharingConfig",
      msg: "creator has been migrated to sharing config"
    },
    {
      code: 6050,
      name: "UnableToDistributeCreatorVaultMigratedToSharingConfig",
      msg: "creator_vault has been migrated to sharing config, use pump:distribute_creator_fees instead"
    },
    {
      code: 6051,
      name: "SharingConfigNotActive",
      msg: "Sharing config is not active"
    },
    {
      code: 6052,
      name: "UnableToDistributeCreatorFeesToExecutableRecipient",
      msg: "The recipient account is executable, so it cannot receive lamports, remove it from the team first"
    },
    {
      code: 6053,
      name: "BondingCurveAndSharingConfigCreatorMismatch",
      msg: "Bonding curve creator does not match sharing config"
    },
    {
      code: 6054,
      name: "ShareholdersAndRemainingAccountsMismatch",
      msg: "Remaining accounts do not match shareholders, make sure to pass exactly the same pubkeys in the same order"
    },
    {
      code: 6055,
      name: "InvalidShareBps",
      msg: "Share bps must be greater than 0"
    },
    {
      code: 6056,
      name: "CashbackNotEnabled",
      msg: "Cashback is not enabled"
    },
    {
      code: 6057,
      name: "BuybackFeeRecipientNotAuthorized",
      msg: "Buyback fee recipient not authorized"
    },
    {
      code: 6058,
      name: "AllBuybackFeeRecipientsShouldBeNonZero"
    },
    {
      code: 6059,
      name: "NotUniqueBuybackFeeRecipients"
    },
    {
      code: 6060,
      name: "BuybackBasisPointsOutOfRange",
      msg: "buyback_basis_points must be <= 10_000"
    },
    {
      code: 6061,
      name: "WrongBuybackFeeRecipientsCount",
      msg: "buyback fee recipients require exactly 8 remaining accounts (or none)"
    },
    {
      code: 6062,
      name: "BuybackFeeRecipientMissing"
    },
    {
      code: 6063,
      name: "UnsupportedQuoteMint",
      msg: "Unsupported quote mint"
    },
    {
      code: 6064,
      name: "InvalidQuoteTokenProgram",
      msg: "Create v2: quote token program must be SPL Token or Token-2022"
    },
    {
      code: 6065,
      name: "InvalidAssociatedQuoteBondingCurve",
      msg: "Create v2: associated quote bonding curve address does not match derivation"
    },
    {
      code: 6066,
      name: "QuoteMintWhitelistFull",
      msg: "Quote mint whitelist is full"
    },
    {
      code: 6067,
      name: "QuoteMintAlreadyWhitelisted",
      msg: "Quote mint is already whitelisted"
    },
    {
      code: 6068,
      name: "QuoteMintNotWhitelisted",
      msg: "Quote mint is not in the whitelist"
    },
    {
      code: 6069,
      name: "QuoteMintNotEligibleForWhitelist",
      msg: "Quote mint cannot be added or removed via whitelist (default or native SOL mint)"
    },
    {
      code: 6070,
      name: "UnableToDistributeCreatorFeesToUninitializedAccount",
      msg: "Unable to distribute creator fees to uninitialized account"
    },
    {
      code: 6071,
      name: "MayhemModeQuoteMintNotAllowed",
      msg: "Mayhem mode quote mint not allowed"
    },
    {
      code: 6072,
      name: "MissingCashbackAccounts",
      msg: "Cashback trade is missing the required remaining accounts"
    },
    {
      code: 6073,
      name: "InvalidCashbackAccumulator",
      msg: "Cashback user_volume_accumulator account is invalid"
    },
    {
      code: 6074,
      name: "InvalidBondingCurveV2",
      msg: "bonding_curve_v2 remaining account is missing or invalid"
    },
    {
      code: 6075,
      name: "InvalidQuoteControl",
      msg: "quote_control remaining account does not match derivation or is uninitialized"
    },
    {
      code: 6076,
      name: "InvalidCashbackRecipient",
      msg: "Cashback recipient token account is not owned by user"
    },
    {
      code: 6077,
      name: "CreatorFeeNotConfigurable",
      msg: "Configurable creator fees are disabled"
    },
    {
      code: 6078,
      name: "CreatorFeeBpsOutOfRange",
      msg: "Creator fee basis points must be between 1 and the configured maximum"
    },
    {
      code: 6079,
      name: "CreatorFeeNotEditable",
      msg: "Creator fee is not editable for this bonding curve"
    },
    {
      code: 6080,
      name: "CreatorFeeNotAllowedForCashbackCoin",
      msg: "Creator fee cannot be configured for a cashback coin"
    },
    {
      code: 6081,
      name: "BondingCurveAlreadyMigrated",
      msg: "Bonding curve has already migrated"
    },
    {
      code: 6082,
      name: "CashbackDeprecated",
      msg: "Cashback coins can no longer be created"
    },
    {
      code: 6083,
      name: "HolderRewardCreatorImmutable",
      msg: "The creator of a holder-reward coin cannot be changed"
    },
    {
      code: 6084,
      name: "HolderRewardDisabled",
      msg: "Holder-reward coins are disabled"
    },
    {
      code: 6085,
      name: "HolderRewardRecipientsMismatch",
      msg: "Holder-reward amounts and recipient accounts do not match"
    },
    {
      code: 6086,
      name: "HolderRewardsRentFloor",
      msg: "The holder-rewards PDA cannot be left below its rent-exempt minimum"
    },
    {
      code: 6087,
      name: "HolderRewardTokenAccountMissing",
      msg: "A holder-rewards token account is required on a token quote"
    },
    {
      code: 6088,
      name: "CtoNotAllowedForMayhemCoin",
      msg: "CTO is not allowed on a mayhem-mode coin"
    },
    {
      code: 6089,
      name: "CtoNewCreatorRequired",
      msg: "new_creator is required unless converting to holder rewards"
    },
    {
      code: 6090,
      name: "CtoNewCreatorNotAllowed",
      msg: "new_creator must be omitted when converting to holder rewards"
    },
    {
      code: 6091,
      name: "CreatorFeeNotConfigurableForQuote",
      msg: "Creator fee is not configurable on a SOL or whitelisted quote; the fee schedule applies"
    },
    {
      code: 6092,
      name: "CtoCreatorAccountNotWritable",
      msg: "current_creator must be passed writable so the outgoing creator can be paid"
    },
    {
      code: 6093,
      name: "CtoSharedVaultFrozen",
      msg: "A frozen sharing-config vault account holds a balance; thaw it before the holder conversion"
    }
  ],
  types: [
    {
      name: "AddQuoteControlMintEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "quote_control",
            type: "pubkey"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "initial_virtual_quote_reserves",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "AdminCtoEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "old_creator",
            type: "pubkey"
          },
          {
            name: "new_creator",
            type: "pubkey"
          },
          {
            name: "is_holder_reward",
            type: "bool"
          },
          {
            name: "is_cashback_coin",
            type: "bool"
          },
          {
            name: "old_creator_fee_bps",
            type: "u64"
          },
          {
            name: "new_creator_fee_bps",
            type: "u64"
          },
          {
            name: "sharing_config_reset",
            type: "bool"
          },
          {
            name: "swept_to_holder_vault",
            type: "u64"
          },
          {
            name: "pool_updated",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "AdminSetIdlAuthorityEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "idl_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "AdminUpdateTokenIncentivesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "start_time",
            type: "i64"
          },
          {
            name: "end_time",
            type: "i64"
          },
          {
            name: "day_number",
            type: "u64"
          },
          {
            name: "token_supply_per_day",
            type: "u64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "seconds_in_a_day",
            type: "i64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "BondingCurve",
      type: {
        kind: "struct",
        fields: [
          {
            name: "virtual_token_reserves",
            type: "u64"
          },
          {
            name: "virtual_quote_reserves",
            type: "u64"
          },
          {
            name: "real_token_reserves",
            type: "u64"
          },
          {
            name: "real_quote_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "complete",
            type: "bool"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          },
          {
            name: "is_cashback_coin",
            type: "bool"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          },
          {
            name: "can_edit_creator_fee",
            type: "bool"
          },
          {
            name: "is_holder_reward",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "ClaimCashbackEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "amount",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "total_claimed",
            type: "u64"
          },
          {
            name: "total_cashback_earned",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "ClaimTokenIncentivesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "amount",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "CloseUserVolumeAccumulatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "total_unclaimed_tokens",
            type: "u64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          },
          {
            name: "last_update_timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "CollectCreatorFeeEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "creator_fee",
            type: "u64"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "CompleteEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "CompletePumpAmmMigrationEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "mint_amount",
            type: "u64"
          },
          {
            name: "sol_amount",
            docs: [
              "The variable is interpreted as `amount` in the offchain services",
              "It is amount in terms of quoteMint for the bondingCurve",
              "The rename is not done yet to avoid breaking changes in offchain services."
            ],
            type: "u64"
          },
          {
            name: "pool_migration_fee",
            type: "u64"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "ConfigStatus",
      type: {
        kind: "enum",
        variants: [
          {
            name: "Paused"
          },
          {
            name: "Active"
          }
        ]
      }
    },
    {
      name: "CreateEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "name",
            type: "string"
          },
          {
            name: "symbol",
            type: "string"
          },
          {
            name: "uri",
            type: "string"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "virtual_token_reserves",
            type: "u64"
          },
          {
            name: "virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "real_token_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "token_program",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          },
          {
            name: "is_cashback_enabled",
            type: "bool"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "virtual_quote_reserves",
            type: "u64"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          },
          {
            name: "is_holder_reward",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "DistributeCreatorFeesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "sharing_config",
            type: "pubkey"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          },
          {
            name: "distributed",
            type: "u64"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "DistributeFeeToHoldersEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "recipients",
            type: "u64"
          },
          {
            name: "total",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "ExtendAccountEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "account",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "current_size",
            type: "u64"
          },
          {
            name: "new_size",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "FeeConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          },
          {
            name: "fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "stable_fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "exotic_flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "FeeTier",
      type: {
        kind: "struct",
        fields: [
          {
            name: "market_cap_lamports_threshold",
            type: "u128"
          },
          {
            name: "fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "Fees",
      type: {
        kind: "struct",
        fields: [
          {
            name: "lp_fee_bps",
            type: "u64"
          },
          {
            name: "protocol_fee_bps",
            type: "u64"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "Global",
      type: {
        kind: "struct",
        fields: [
          {
            name: "initialized",
            docs: [
              "Unused"
            ],
            type: "bool"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "fee_recipient",
            type: "pubkey"
          },
          {
            name: "initial_virtual_token_reserves",
            type: "u64"
          },
          {
            name: "initial_virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "initial_real_token_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "fee_basis_points",
            type: "u64"
          },
          {
            name: "withdraw_authority",
            type: "pubkey"
          },
          {
            name: "enable_migrate",
            docs: [
              "Unused"
            ],
            type: "bool"
          },
          {
            name: "pool_migration_fee",
            type: "u64"
          },
          {
            name: "creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          },
          {
            name: "set_creator_authority",
            type: "pubkey"
          },
          {
            name: "admin_set_creator_authority",
            type: "pubkey"
          },
          {
            name: "create_v2_enabled",
            type: "bool"
          },
          {
            name: "whitelist_pda",
            type: "pubkey"
          },
          {
            name: "reserved_fee_recipient",
            type: "pubkey"
          },
          {
            name: "mayhem_mode_enabled",
            type: "bool"
          },
          {
            name: "reserved_fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          },
          {
            name: "is_cashback_enabled",
            type: "bool"
          },
          {
            name: "buyback_fee_recipients",
            type: {
              array: [
                "pubkey",
                8
              ]
            }
          },
          {
            name: "buyback_basis_points",
            type: "u64"
          },
          {
            name: "initial_virtual_quote_reserves",
            type: "u64"
          },
          {
            name: "whitelisted_quote_mints",
            type: {
              array: [
                "pubkey",
                1
              ]
            }
          },
          {
            name: "creator_fee_configurable",
            type: "bool"
          },
          {
            name: "max_configurable_creator_fee_bps",
            type: "u64"
          },
          {
            name: "holder_reward_claim_authority",
            type: "pubkey"
          },
          {
            name: "is_holder_reward_enabled",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "GlobalVolumeAccumulator",
      type: {
        kind: "struct",
        fields: [
          {
            name: "start_time",
            type: "i64"
          },
          {
            name: "end_time",
            type: "i64"
          },
          {
            name: "seconds_in_a_day",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "total_token_supply",
            type: {
              array: [
                "u64",
                30
              ]
            }
          },
          {
            name: "sol_volumes",
            type: {
              array: [
                "u64",
                30
              ]
            }
          }
        ]
      }
    },
    {
      name: "InitUserVolumeAccumulatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "payer",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "MigrateBondingCurveCreatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "sharing_config",
            type: "pubkey"
          },
          {
            name: "old_creator",
            type: "pubkey"
          },
          {
            name: "new_creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "MinimumDistributableFeeEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "minimum_required",
            type: "u64"
          },
          {
            name: "distributable_fees",
            type: "u64"
          },
          {
            name: "can_distribute",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "OptionBool",
      type: {
        kind: "struct",
        fields: [
          "bool"
        ]
      }
    },
    {
      name: "OptionU64",
      type: {
        kind: "struct",
        fields: [
          "u64"
        ]
      }
    },
    {
      name: "QuoteControl",
      type: {
        kind: "struct",
        fields: [
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "_reserved",
            type: {
              array: [
                "u8",
                64
              ]
            }
          },
          {
            name: "mints",
            type: {
              vec: {
                defined: {
                  name: "QuoteControlMint"
                }
              }
            }
          }
        ]
      }
    },
    {
      name: "QuoteControlMint",
      type: {
        kind: "struct",
        fields: [
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "initial_virtual_quote_reserves",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "RemoveQuoteControlMintEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "quote_control",
            type: "pubkey"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "ReservedFeeRecipientsEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "reserved_fee_recipient",
            type: "pubkey"
          },
          {
            name: "reserved_fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          }
        ]
      }
    },
    {
      name: "SetCreatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SetMetaplexCreatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "metadata",
            type: "pubkey"
          },
          {
            name: "creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SetParamsEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "initial_virtual_token_reserves",
            type: "u64"
          },
          {
            name: "initial_virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "initial_real_token_reserves",
            type: "u64"
          },
          {
            name: "final_real_sol_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "fee_basis_points",
            type: "u64"
          },
          {
            name: "withdraw_authority",
            type: "pubkey"
          },
          {
            name: "enable_migrate",
            type: "bool"
          },
          {
            name: "pool_migration_fee",
            type: "u64"
          },
          {
            name: "creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "fee_recipients",
            type: {
              array: [
                "pubkey",
                8
              ]
            }
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "set_creator_authority",
            type: "pubkey"
          },
          {
            name: "admin_set_creator_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SetQuoteControlAdminEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "quote_control",
            type: "pubkey"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "old_admin",
            type: "pubkey"
          },
          {
            name: "new_admin",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "Shareholder",
      type: {
        kind: "struct",
        fields: [
          {
            name: "address",
            type: "pubkey"
          },
          {
            name: "share_bps",
            type: "u16"
          }
        ]
      }
    },
    {
      name: "SharingConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "version",
            type: "u8"
          },
          {
            name: "status",
            type: {
              defined: {
                name: "ConfigStatus"
              }
            }
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "admin_revoked",
            type: "bool"
          },
          {
            name: "shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          }
        ]
      }
    },
    {
      name: "SyncUserVolumeAccumulatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "total_claimed_tokens_before",
            type: "u64"
          },
          {
            name: "total_claimed_tokens_after",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "TradeEvent",
      docs: [
        'ix_name: "buy" | "sell" | "buy_exact_sol_in"'
      ],
      type: {
        kind: "struct",
        fields: [
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "sol_amount",
            type: "u64"
          },
          {
            name: "token_amount",
            type: "u64"
          },
          {
            name: "is_buy",
            type: "bool"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "virtual_token_reserves",
            type: "u64"
          },
          {
            name: "real_sol_reserves",
            type: "u64"
          },
          {
            name: "real_token_reserves",
            type: "u64"
          },
          {
            name: "fee_recipient",
            type: "pubkey"
          },
          {
            name: "fee_basis_points",
            type: "u64"
          },
          {
            name: "fee",
            type: "u64"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "creator_fee",
            type: "u64"
          },
          {
            name: "track_volume",
            type: "bool"
          },
          {
            name: "total_unclaimed_tokens",
            type: "u64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          },
          {
            name: "last_update_timestamp",
            type: "i64"
          },
          {
            name: "ix_name",
            type: "string"
          },
          {
            name: "mayhem_mode",
            type: "bool"
          },
          {
            name: "cashback_fee_basis_points",
            type: "u64"
          },
          {
            name: "cashback",
            type: "u64"
          },
          {
            name: "buyback_fee_basis_points",
            type: "u64"
          },
          {
            name: "buyback_fee",
            type: "u64"
          },
          {
            name: "shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "quote_amount",
            type: "u64"
          },
          {
            name: "virtual_quote_reserves",
            type: "u64"
          },
          {
            name: "real_quote_reserves",
            type: "u64"
          },
          {
            name: "holder_rewards_bps",
            type: "u64"
          },
          {
            name: "holder_rewards",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "UpdateCreatorFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "creator_fee_configurable",
            type: "bool"
          },
          {
            name: "max_configurable_creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "UpdateGlobalAuthorityEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "global",
            type: "pubkey"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "new_authority",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "UpdateMayhemVirtualParamsEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "virtual_token_reserves",
            type: "u64"
          },
          {
            name: "virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "new_virtual_token_reserves",
            type: "u64"
          },
          {
            name: "new_virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "real_token_reserves",
            type: "u64"
          },
          {
            name: "real_sol_reserves",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "UserVolumeAccumulator",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "needs_claim",
            type: "bool"
          },
          {
            name: "total_unclaimed_tokens",
            type: "u64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          },
          {
            name: "last_update_timestamp",
            type: "i64"
          },
          {
            name: "has_total_claimed_tokens",
            type: "bool"
          },
          {
            name: "cashback_earned",
            type: "u64"
          },
          {
            name: "total_cashback_claimed",
            type: "u64"
          },
          {
            name: "stable_cashback_earned",
            type: "u64"
          },
          {
            name: "total_stable_cashback_claimed",
            type: "u64"
          }
        ]
      }
    }
  ]
};

// src/bondingCurve.ts
var import_spl_token5 = require("@solana/spl-token");
var import_web35 = require("@solana/web3.js");
var import_bn5 = __toESM(require("bn.js"));

// src/errors.ts
var NoShareholdersError = class extends Error {
  constructor() {
    super("No shareholders provided");
    this.name = "NoShareholdersError";
  }
};
var TooManyShareholdersError = class extends Error {
  constructor(count, max) {
    super(`Too many shareholders. Maximum allowed is ${max}, got ${count}`);
    this.count = count;
    this.max = max;
    this.name = "TooManyShareholdersError";
  }
};
var ZeroShareError = class extends Error {
  constructor(address) {
    super(`Zero or negative share not allowed for address ${address}`);
    this.address = address;
    this.name = "ZeroShareError";
  }
};
var ShareCalculationOverflowError = class extends Error {
  constructor() {
    super("Share calculation overflow - total shares exceed maximum value");
    this.name = "ShareCalculationOverflowError";
  }
};
var InvalidShareTotalError = class extends Error {
  constructor(total) {
    super(
      `Invalid share total. Must equal 10,000 basis points (100%). Got ${total}`
    );
    this.total = total;
    this.name = "InvalidShareTotalError";
  }
};
var DuplicateShareholderError = class extends Error {
  constructor() {
    super("Duplicate shareholder addresses not allowed");
    this.name = "DuplicateShareholderError";
  }
};
var PoolRequiredForGraduatedError = class extends Error {
  constructor() {
    super(
      "Pool parameter is required for graduated coins (bondingCurve.complete = true)"
    );
    this.name = "PoolRequiredForGraduatedError";
  }
};
var UnsupportedQuoteMintError = class extends Error {
  constructor(quoteMint) {
    super(
      `Unsupported quote mint ${quoteMint.toBase58()}: not SOL, not whitelisted on Global and not listed in QuoteControl`
    );
    this.quoteMint = quoteMint;
    this.name = "UnsupportedQuoteMintError";
  }
};
var CreatorFeeNotConfigurableError = class extends Error {
  constructor() {
    super(
      "Configurable creator fees are disabled (Global.creatorFeeConfigurable is false)"
    );
    this.name = "CreatorFeeNotConfigurableError";
  }
};
var CreatorFeeBpsOutOfRangeError = class extends Error {
  constructor(creatorFeeBps, max) {
    super(
      `Creator fee of ${creatorFeeBps.toString()} bps is outside 1..=${max.toString()} (Global.maxConfigurableCreatorFeeBps)`
    );
    this.creatorFeeBps = creatorFeeBps;
    this.max = max;
    this.name = "CreatorFeeBpsOutOfRangeError";
  }
};
var CreatorFeeNotAllowedForCashbackCoinError = class extends Error {
  constructor(mint) {
    super(
      `Creator fee cannot be configured for cashback coin ${mint.toBase58()}`
    );
    this.mint = mint;
    this.name = "CreatorFeeNotAllowedForCashbackCoinError";
  }
};
var CashbackDeprecatedError = class extends Error {
  constructor(mint) {
    super(
      `Cashback coins can no longer be created (mint ${mint.toBase58()}): is_cashback_enabled is deprecated`
    );
    this.mint = mint;
    this.name = "CashbackDeprecatedError";
  }
};
var HolderRewardDisabledError = class extends Error {
  constructor() {
    super(
      "Holder-reward coins are disabled (Global.isHolderRewardEnabled is false)"
    );
    this.name = "HolderRewardDisabledError";
  }
};
var HolderRewardCreatorImmutableError = class extends Error {
  constructor(mint) {
    super(
      `The creator of holder-reward coin ${mint.toBase58()} cannot be changed`
    );
    this.mint = mint;
    this.name = "HolderRewardCreatorImmutableError";
  }
};
var CtoNotAllowedForMayhemCoinError = class extends Error {
  constructor(mint) {
    super(`CTO is not allowed on mayhem-mode coin ${mint.toBase58()}`);
    this.mint = mint;
    this.name = "CtoNotAllowedForMayhemCoinError";
  }
};
var CreatorFeeNotConfigurableForQuoteError = class extends Error {
  constructor(quoteMint) {
    super(
      `Creator fee is not configurable on quote mint ${quoteMint.toBase58()} (SOL or whitelisted); the fee schedule applies`
    );
    this.quoteMint = quoteMint;
    this.name = "CreatorFeeNotConfigurableForQuoteError";
  }
};

// src/fees.ts
var import_spl_token = require("@solana/spl-token");
var import_web3 = require("@solana/web3.js");
var import_bn = __toESM(require("bn.js"));
var ONE_BILLION_SUPPLY = new import_bn.default(1e15);
var SOL_LIKE_QUOTE_MINTS = Object.freeze([
  import_web3.PublicKey.default,
  import_spl_token.NATIVE_MINT,
  import_spl_token.NATIVE_MINT_2022
]);
var STABLE_QUOTE_MINTS = Object.freeze([
  new import_web3.PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
]);
function isSolLikeQuoteMint(quoteMint) {
  return SOL_LIKE_QUOTE_MINTS.some((mint) => mint.equals(quoteMint));
}
function isStableQuoteMint(quoteMint) {
  return STABLE_QUOTE_MINTS.some((mint) => mint.equals(quoteMint));
}
function isExoticQuoteMint(quoteMint) {
  return !isSolLikeQuoteMint(quoteMint) && !isStableQuoteMint(quoteMint);
}
function getFee({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  isNewBondingCurve
}) {
  const { virtualQuoteReserves, virtualTokenReserves, isMayhemMode } = bondingCurve;
  const { protocolFeeBps, creatorFeeBps } = computeFeesBps({
    global,
    feeConfig,
    mintSupply: isMayhemMode ? mintSupply : ONE_BILLION_SUPPLY,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint: bondingCurve.quoteMint,
    creatorFeeBps: bondingCurve.creatorFeeBps
  });
  return fee(amount, protocolFeeBps).add(
    isNewBondingCurve || !import_web3.PublicKey.default.equals(bondingCurve.creator) ? fee(amount, creatorFeeBps) : new import_bn.default(0)
  );
}
function computeFeesBps({
  global,
  feeConfig,
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
  quoteMint,
  creatorFeeBps
}) {
  const schedule = scheduleFeesBps({
    global,
    feeConfig,
    mintSupply,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint
  });
  if (!global.creatorFeeConfigurable || creatorFeeBps == null || creatorFeeBps.isZero()) {
    return schedule;
  }
  return { protocolFeeBps: schedule.protocolFeeBps, creatorFeeBps };
}
function scheduleFeesBps({
  global,
  feeConfig,
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves,
  quoteMint
}) {
  if (feeConfig != null) {
    const marketCap = bondingCurveMarketCap({
      mintSupply,
      virtualQuoteReserves,
      virtualTokenReserves
    });
    return selectCurveFeeSchedule({
      feeConfig,
      quoteMint: quoteMint ?? import_web3.PublicKey.default,
      marketCap
    });
  }
  return {
    protocolFeeBps: global.feeBasisPoints,
    creatorFeeBps: global.creatorFeeBasisPoints
  };
}
function selectCurveFeeSchedule({
  feeConfig,
  quoteMint,
  marketCap
}) {
  if (isSolLikeQuoteMint(quoteMint)) {
    return calculateFeeTier({ feeTiers: feeConfig.feeTiers, marketCap });
  }
  if (isStableQuoteMint(quoteMint)) {
    return calculateFeeTier({
      feeTiers: feeConfig.stableFeeTiers.length > 0 ? feeConfig.stableFeeTiers : feeConfig.feeTiers,
      marketCap
    });
  }
  return isZeroFees(feeConfig.exoticFlatFees) ? feeConfig.flatFees : feeConfig.exoticFlatFees;
}
function isZeroFees({ lpFeeBps, protocolFeeBps, creatorFeeBps }) {
  return lpFeeBps.isZero() && protocolFeeBps.isZero() && creatorFeeBps.isZero();
}
function calculateFeeTier({
  feeTiers,
  marketCap
}) {
  if (feeTiers.length === 0) {
    throw new Error("Fee tiers cannot be empty");
  }
  const firstTier = feeTiers[0];
  if (marketCap.lt(firstTier.marketCapLamportsThreshold)) {
    return firstTier.fees;
  }
  for (const tier of feeTiers.slice().reverse()) {
    if (marketCap.gte(tier.marketCapLamportsThreshold)) {
      return tier.fees;
    }
  }
  return firstTier.fees;
}
function fee(amount, feeBasisPoints) {
  return ceilDiv(amount.mul(feeBasisPoints), new import_bn.default(1e4));
}
function ceilDiv(a, b) {
  return a.add(b.subn(1)).div(b);
}
function getFeeRecipient(global, mayhemMode) {
  if (mayhemMode) {
    const feeRecipients2 = [
      global.reservedFeeRecipient,
      ...global.reservedFeeRecipients
    ];
    return feeRecipients2[Math.floor(Math.random() * feeRecipients2.length)];
  }
  const feeRecipients = [global.feeRecipient, ...global.feeRecipients];
  return feeRecipients[Math.floor(Math.random() * feeRecipients.length)];
}

// src/pda.ts
var import_pump_swap_sdk3 = require("@pump-fun/pump-swap-sdk");
var import_spl_token4 = require("@solana/spl-token");
var import_web34 = require("@solana/web3.js");
var import_buffer = require("buffer");

// src/sdk.ts
var import_anchor = require("@coral-xyz/anchor");
var import_agent_payments_sdk = require("@pump-fun/agent-payments-sdk");
var import_pump_swap_sdk2 = require("@pump-fun/pump-swap-sdk");
var import_spl_token3 = require("@solana/spl-token");
var import_web33 = require("@solana/web3.js");
var import_bn4 = __toESM(require("bn.js"));

// src/idl/pump_amm.json
var pump_amm_default = {
  address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
  metadata: {
    name: "pump_amm",
    version: "0.1.0",
    spec: "0.1.0",
    description: "Created with Anchor"
  },
  instructions: [
    {
      name: "admin_cto_pool",
      discriminator: [
        45,
        61,
        165,
        151,
        104,
        0,
        49,
        189
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "global_config"
        },
        {
          name: "pool",
          writable: true
        },
        {
          name: "pool_authority",
          signer: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              },
              {
                kind: "account",
                path: "pool.base_mint",
                account: "Pool"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "coin_creator",
          type: "pubkey"
        },
        {
          name: "is_holder_reward",
          type: "bool"
        },
        {
          name: "creator_fee_bps",
          type: {
            option: "u64"
          }
        }
      ]
    },
    {
      name: "admin_update_token_incentives",
      discriminator: [
        209,
        11,
        115,
        87,
        213,
        23,
        124,
        204
      ],
      accounts: [
        {
          name: "admin",
          writable: true,
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ]
          }
        },
        {
          name: "global_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "mint"
        },
        {
          name: "global_incentive_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "global_volume_accumulator"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "start_time",
          type: "i64"
        },
        {
          name: "end_time",
          type: "i64"
        },
        {
          name: "seconds_in_a_day",
          type: "i64"
        },
        {
          name: "day_number",
          type: "u64"
        },
        {
          name: "token_supply_per_day",
          type: "u64"
        }
      ]
    },
    {
      name: "boost_buy_and_burn",
      discriminator: [
        105,
        68,
        6,
        175,
        0,
        7,
        35,
        162
      ],
      accounts: [
        {
          name: "pool"
        },
        {
          name: "authority",
          writable: true,
          signer: true
        },
        {
          name: "global_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ]
          }
        },
        {
          name: "base_mint",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_base_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "boost_vault_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  111,
                  115,
                  116,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool"
              }
            ]
          }
        },
        {
          name: "boost_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "boost_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "quote_amount_in",
          type: "u64"
        },
        {
          name: "min_base_amount_burned",
          type: "u64"
        }
      ]
    },
    {
      name: "buy",
      docs: [
        "For cashback coins, optionally pass user_volume_accumulator_wsol_ata as remaining_accounts[0].",
        "If provided and valid, the ATA will be initialized if needed."
      ],
      discriminator: [
        102,
        6,
        61,
        18,
        1,
        218,
        235,
        234
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "global_config"
        },
        {
          name: "base_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "user_base_token_account",
          writable: true
        },
        {
          name: "user_quote_token_account",
          writable: true
        },
        {
          name: "pool_base_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "protocol_fee_recipient"
        },
        {
          name: "protocol_fee_recipient_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "protocol_fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "coin_creator_vault_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool.coin_creator",
                account: "Pool"
              }
            ]
          }
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  12,
                  20,
                  222,
                  252,
                  130,
                  94,
                  198,
                  118,
                  148,
                  37,
                  8,
                  24,
                  187,
                  101,
                  64,
                  101,
                  244,
                  41,
                  141,
                  49,
                  86,
                  213,
                  113,
                  180,
                  212,
                  248,
                  9,
                  12,
                  24,
                  233,
                  168,
                  99
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "base_amount_out",
          type: "u64"
        },
        {
          name: "max_quote_amount_in",
          type: "u64"
        },
        {
          name: "track_volume",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ]
    },
    {
      name: "buy_exact_quote_in",
      docs: [
        "Given a budget of spendable_quote_in, buy at least min_base_amount_out",
        "Fees will be deducted from spendable_quote_in",
        "",
        "f(quote) = tokens, where tokens >= min_base_amount_out",
        "",
        "Make sure the payer has enough SOL to cover creation of the following accounts (unless already created):",
        "- protocol_fee_recipient_token_account: rent.minimum_balance(TokenAccount::LEN)",
        "- coin_creator_vault_ata: rent.minimum_balance(TokenAccount::LEN)",
        "- user_volume_accumulator: rent.minimum_balance(UserVolumeAccumulator::LEN)",
        "",
        "For cashback coins, optionally pass user_volume_accumulator_wsol_ata as remaining_accounts[0].",
        "If provided and valid, the ATA will be initialized if needed."
      ],
      discriminator: [
        198,
        46,
        21,
        82,
        180,
        217,
        232,
        112
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "global_config"
        },
        {
          name: "base_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "user_base_token_account",
          writable: true
        },
        {
          name: "user_quote_token_account",
          writable: true
        },
        {
          name: "pool_base_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "protocol_fee_recipient"
        },
        {
          name: "protocol_fee_recipient_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "protocol_fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "coin_creator_vault_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool.coin_creator",
                account: "Pool"
              }
            ]
          }
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  12,
                  20,
                  222,
                  252,
                  130,
                  94,
                  198,
                  118,
                  148,
                  37,
                  8,
                  24,
                  187,
                  101,
                  64,
                  101,
                  244,
                  41,
                  141,
                  49,
                  86,
                  213,
                  113,
                  180,
                  212,
                  248,
                  9,
                  12,
                  24,
                  233,
                  168,
                  99
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "spendable_quote_in",
          type: "u64"
        },
        {
          name: "min_base_amount_out",
          type: "u64"
        },
        {
          name: "track_volume",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ]
    },
    {
      name: "claim_cashback",
      docs: [
        "Pays out the user's accrued cashback. `user_wsol_token_account` may be any token account",
        "of `quote_mint` owned by `user`, not only the associated one."
      ],
      discriminator: [
        37,
        58,
        35,
        126,
        190,
        53,
        228,
        197
      ],
      accounts: [
        {
          name: "user",
          writable: true
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "user_volume_accumulator_wsol_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user_volume_accumulator"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user_wsol_token_account",
          writable: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        }
      ],
      args: []
    },
    {
      name: "claim_token_incentives",
      discriminator: [
        16,
        4,
        71,
        28,
        204,
        1,
        40,
        27
      ],
      accounts: [
        {
          name: "user"
        },
        {
          name: "user_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "user"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "global_incentive_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "global_volume_accumulator"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "mint",
          relations: [
            "global_volume_accumulator"
          ]
        },
        {
          name: "token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "payer",
          writable: true,
          signer: true
        }
      ],
      args: []
    },
    {
      name: "close_user_volume_accumulator",
      discriminator: [
        249,
        69,
        164,
        218,
        150,
        103,
        84,
        138
      ],
      accounts: [
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "collect_coin_creator_fee",
      discriminator: [
        160,
        57,
        89,
        42,
        181,
        139,
        43,
        66
      ],
      accounts: [
        {
          name: "quote_mint"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "coin_creator"
        },
        {
          name: "coin_creator_vault_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "coin_creator"
              }
            ]
          }
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "coin_creator_token_account",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "create_config",
      discriminator: [
        201,
        207,
        243,
        114,
        75,
        111,
        47,
        189
      ],
      accounts: [
        {
          name: "admin",
          writable: true,
          signer: true,
          address: "8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8"
        },
        {
          name: "global_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "lp_fee_basis_points",
          type: "u64"
        },
        {
          name: "protocol_fee_basis_points",
          type: "u64"
        },
        {
          name: "protocol_fee_recipients",
          type: {
            array: [
              "pubkey",
              8
            ]
          }
        },
        {
          name: "coin_creator_fee_basis_points",
          type: "u64"
        },
        {
          name: "admin_set_coin_creator_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "create_pool",
      discriminator: [
        233,
        146,
        209,
        142,
        207,
        104,
        64,
        188
      ],
      accounts: [
        {
          name: "pool",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108
                ]
              },
              {
                kind: "arg",
                path: "index"
              },
              {
                kind: "account",
                path: "creator"
              },
              {
                kind: "account",
                path: "base_mint"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ]
          }
        },
        {
          name: "global_config"
        },
        {
          name: "creator",
          writable: true,
          signer: true
        },
        {
          name: "base_mint"
        },
        {
          name: "quote_mint"
        },
        {
          name: "lp_mint",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  95,
                  108,
                  112,
                  95,
                  109,
                  105,
                  110,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool"
              }
            ]
          }
        },
        {
          name: "user_base_token_account",
          writable: true
        },
        {
          name: "user_quote_token_account",
          writable: true
        },
        {
          name: "user_pool_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "creator"
              },
              {
                kind: "account",
                path: "token_2022_program"
              },
              {
                kind: "account",
                path: "lp_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "pool_base_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool"
              },
              {
                kind: "account",
                path: "base_token_program"
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pool"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_2022_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "index",
          type: "u16"
        },
        {
          name: "base_amount_in",
          type: "u64"
        },
        {
          name: "quote_amount_in",
          type: "u64"
        },
        {
          name: "coin_creator",
          type: "pubkey"
        },
        {
          name: "is_mayhem_mode",
          type: "bool"
        },
        {
          name: "is_cashback_coin",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        },
        {
          name: "creator_fee_bps",
          type: {
            defined: {
              name: "OptionU64"
            }
          }
        },
        {
          name: "can_edit_creator_fee",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        },
        {
          name: "is_holder_reward",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ]
    },
    {
      name: "deposit",
      discriminator: [
        242,
        35,
        198,
        137,
        82,
        225,
        242,
        182
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "global_config"
        },
        {
          name: "user",
          signer: true
        },
        {
          name: "base_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "lp_mint",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "user_base_token_account",
          writable: true
        },
        {
          name: "user_quote_token_account",
          writable: true
        },
        {
          name: "user_pool_token_account",
          writable: true
        },
        {
          name: "pool_base_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "token_program",
          address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        },
        {
          name: "token_2022_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "lp_token_amount_out",
          type: "u64"
        },
        {
          name: "max_base_amount_in",
          type: "u64"
        },
        {
          name: "max_quote_amount_in",
          type: "u64"
        }
      ]
    },
    {
      name: "disable",
      discriminator: [
        185,
        173,
        187,
        90,
        216,
        15,
        238,
        233
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "disable_create_pool",
          type: "bool"
        },
        {
          name: "disable_deposit",
          type: "bool"
        },
        {
          name: "disable_withdraw",
          type: "bool"
        },
        {
          name: "disable_buy",
          type: "bool"
        },
        {
          name: "disable_sell",
          type: "bool"
        }
      ]
    },
    {
      name: "extend_account",
      discriminator: [
        234,
        102,
        194,
        203,
        150,
        72,
        62,
        229
      ],
      accounts: [
        {
          name: "account",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "init_boost",
      discriminator: [
        140,
        233,
        33,
        94,
        132,
        90,
        194,
        143
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "global_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ]
          }
        },
        {
          name: "creator",
          writable: true,
          signer: true
        },
        {
          name: "base_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_base_token_account",
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "boost_vault_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  111,
                  115,
                  116,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool"
              }
            ]
          }
        },
        {
          name: "boost_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "boost_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "quote_token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "init_user_volume_accumulator",
      discriminator: [
        94,
        6,
        202,
        115,
        255,
        96,
        232,
        183
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "user"
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "migrate_pool_coin_creator",
      docs: [
        "Migrate Pool Coin Creator to Sharing Config"
      ],
      discriminator: [
        208,
        8,
        159,
        4,
        74,
        175,
        16,
        58
      ],
      accounts: [
        {
          name: "pool",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108
                ]
              },
              {
                kind: "account",
                path: "pool.index",
                account: "Pool"
              },
              {
                kind: "account",
                path: "pool.creator",
                account: "Pool"
              },
              {
                kind: "account",
                path: "pool.base_mint",
                account: "Pool"
              },
              {
                kind: "account",
                path: "pool.quote_mint",
                account: "Pool"
              }
            ]
          }
        },
        {
          name: "sharing_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "pool.base_mint",
                account: "Pool"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                53,
                255,
                169,
                5,
                90,
                142,
                86,
                141,
                168,
                247,
                188,
                7,
                86,
                21,
                39,
                76,
                241,
                201,
                44,
                164,
                31,
                64,
                0,
                156,
                81,
                106,
                164,
                20,
                194,
                124,
                112
              ]
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "sell",
      discriminator: [
        51,
        230,
        133,
        164,
        1,
        127,
        131,
        173
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "user",
          writable: true,
          signer: true
        },
        {
          name: "global_config"
        },
        {
          name: "base_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "user_base_token_account",
          writable: true
        },
        {
          name: "user_quote_token_account",
          writable: true
        },
        {
          name: "pool_base_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "protocol_fee_recipient"
        },
        {
          name: "protocol_fee_recipient_token_account",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "protocol_fee_recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "base_token_program"
        },
        {
          name: "quote_token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "coin_creator_vault_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "pool.coin_creator",
                account: "Pool"
              }
            ]
          }
        },
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "const",
                value: [
                  12,
                  20,
                  222,
                  252,
                  130,
                  94,
                  198,
                  118,
                  148,
                  37,
                  8,
                  24,
                  187,
                  101,
                  64,
                  101,
                  244,
                  41,
                  141,
                  49,
                  86,
                  213,
                  113,
                  180,
                  212,
                  248,
                  9,
                  12,
                  24,
                  233,
                  168,
                  99
                ]
              }
            ],
            program: {
              kind: "account",
              path: "fee_program"
            }
          }
        },
        {
          name: "fee_program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "base_amount_in",
          type: "u64"
        },
        {
          name: "min_quote_amount_out",
          type: "u64"
        }
      ]
    },
    {
      name: "set_boost_authority",
      discriminator: [
        227,
        149,
        76,
        42,
        130,
        39,
        234,
        205
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "boost_authority"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "set_coin_creator",
      docs: [
        "Sets Pool::coin_creator from Metaplex metadata creator or BondingCurve::creator"
      ],
      discriminator: [
        210,
        149,
        128,
        45,
        188,
        58,
        78,
        175
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "metadata",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  109,
                  101,
                  116,
                  97,
                  100,
                  97,
                  116,
                  97
                ]
              },
              {
                kind: "const",
                value: [
                  11,
                  112,
                  101,
                  177,
                  227,
                  209,
                  124,
                  69,
                  56,
                  157,
                  82,
                  127,
                  107,
                  4,
                  195,
                  205,
                  88,
                  184,
                  108,
                  115,
                  26,
                  160,
                  253,
                  181,
                  73,
                  182,
                  209,
                  188,
                  3,
                  248,
                  41,
                  70
                ]
              },
              {
                kind: "account",
                path: "pool.base_mint",
                account: "Pool"
              }
            ],
            program: {
              kind: "const",
              value: [
                11,
                112,
                101,
                177,
                227,
                209,
                124,
                69,
                56,
                157,
                82,
                127,
                107,
                4,
                195,
                205,
                88,
                184,
                108,
                115,
                26,
                160,
                253,
                181,
                73,
                182,
                209,
                188,
                3,
                248,
                41,
                70
              ]
            }
          }
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "pool.base_mint",
                account: "Pool"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "set_reserved_fee_recipients",
      discriminator: [
        111,
        172,
        162,
        232,
        114,
        89,
        213,
        142
      ],
      accounts: [
        {
          name: "global_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              }
            ]
          }
        },
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "whitelist_pda",
          type: "pubkey"
        }
      ]
    },
    {
      name: "sync_user_volume_accumulator",
      discriminator: [
        86,
        31,
        192,
        87,
        163,
        87,
        79,
        238
      ],
      accounts: [
        {
          name: "user"
        },
        {
          name: "global_volume_accumulator",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              }
            ]
          }
        },
        {
          name: "user_volume_accumulator",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  117,
                  115,
                  101,
                  114,
                  95,
                  118,
                  111,
                  108,
                  117,
                  109,
                  101,
                  95,
                  97,
                  99,
                  99,
                  117,
                  109,
                  117,
                  108,
                  97,
                  116,
                  111,
                  114
                ]
              },
              {
                kind: "account",
                path: "user"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "toggle_boost",
      discriminator: [
        117,
        161,
        160,
        74,
        223,
        137,
        118,
        99
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        }
      ],
      args: [
        {
          name: "enabled",
          type: "bool"
        }
      ]
    },
    {
      name: "toggle_cashback_enabled",
      discriminator: [
        115,
        103,
        224,
        255,
        189,
        89,
        86,
        195
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "enabled",
          type: "bool"
        }
      ]
    },
    {
      name: "toggle_mayhem_mode",
      discriminator: [
        1,
        9,
        111,
        208,
        100,
        31,
        255,
        163
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "enabled",
          type: "bool"
        }
      ]
    },
    {
      name: "transfer_creator_fees_to_pump",
      docs: [
        "Transfer creator fees to pump creator vault",
        "If coin creator fees are currently below rent.minimum_balance(TokenAccount::LEN)",
        "The transfer will be skipped"
      ],
      discriminator: [
        139,
        52,
        134,
        85,
        228,
        229,
        108,
        241
      ],
      accounts: [
        {
          name: "wsol_mint",
          docs: [
            "Pump Canonical Pool are quoted in wSOL"
          ]
        },
        {
          name: "token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "coin_creator"
        },
        {
          name: "coin_creator_vault_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "coin_creator"
              }
            ]
          }
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "wsol_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "pump_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "coin_creator"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "transfer_creator_fees_to_pump_v2",
      discriminator: [
        1,
        33,
        78,
        185,
        33,
        67,
        44,
        92
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "quote_mint"
        },
        {
          name: "token_program"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "coin_creator"
        },
        {
          name: "coin_creator_vault_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "coin_creator"
              }
            ]
          }
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "pump_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "coin_creator"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pump_creator_vault"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "update_admin",
      discriminator: [
        161,
        176,
        40,
        213,
        60,
        184,
        179,
        228
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "new_admin"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "update_buyback_config",
      discriminator: [
        251,
        224,
        171,
        146,
        160,
        26,
        113,
        233
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "buyback_basis_points",
          type: {
            option: "u64"
          }
        }
      ]
    },
    {
      name: "update_creator_fee_config",
      discriminator: [
        61,
        175,
        160,
        249,
        66,
        66,
        136,
        175
      ],
      accounts: [
        {
          name: "admin",
          writable: true,
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "creator_fee_configurable",
          type: "bool"
        },
        {
          name: "max_configurable_creator_fee_bps",
          type: "u64"
        }
      ]
    },
    {
      name: "update_fee_config",
      discriminator: [
        104,
        184,
        103,
        242,
        88,
        151,
        107,
        20
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "global_config"
          ]
        },
        {
          name: "global_config",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "lp_fee_basis_points",
          type: "u64"
        },
        {
          name: "protocol_fee_basis_points",
          type: "u64"
        },
        {
          name: "protocol_fee_recipients",
          type: {
            array: [
              "pubkey",
              8
            ]
          }
        },
        {
          name: "coin_creator_fee_basis_points",
          type: "u64"
        },
        {
          name: "admin_set_coin_creator_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "withdraw",
      discriminator: [
        183,
        18,
        70,
        156,
        148,
        109,
        161,
        34
      ],
      accounts: [
        {
          name: "pool",
          writable: true
        },
        {
          name: "global_config"
        },
        {
          name: "user",
          signer: true
        },
        {
          name: "base_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "quote_mint",
          relations: [
            "pool"
          ]
        },
        {
          name: "lp_mint",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "user_base_token_account",
          writable: true
        },
        {
          name: "user_quote_token_account",
          writable: true
        },
        {
          name: "user_pool_token_account",
          writable: true
        },
        {
          name: "pool_base_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "pool_quote_token_account",
          writable: true,
          relations: [
            "pool"
          ]
        },
        {
          name: "token_program",
          address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        },
        {
          name: "token_2022_program",
          address: "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "lp_token_amount_in",
          type: "u64"
        },
        {
          name: "min_base_amount_out",
          type: "u64"
        },
        {
          name: "min_quote_amount_out",
          type: "u64"
        }
      ]
    }
  ],
  accounts: [
    {
      name: "BondingCurve",
      discriminator: [
        23,
        183,
        248,
        55,
        96,
        216,
        172,
        96
      ]
    },
    {
      name: "FeeConfig",
      discriminator: [
        143,
        52,
        146,
        187,
        219,
        123,
        76,
        155
      ]
    },
    {
      name: "GlobalConfig",
      discriminator: [
        149,
        8,
        156,
        202,
        160,
        252,
        176,
        217
      ]
    },
    {
      name: "GlobalVolumeAccumulator",
      discriminator: [
        202,
        42,
        246,
        43,
        142,
        190,
        30,
        255
      ]
    },
    {
      name: "Pool",
      discriminator: [
        241,
        154,
        109,
        4,
        17,
        177,
        109,
        188
      ]
    },
    {
      name: "SharingConfig",
      discriminator: [
        216,
        74,
        9,
        0,
        56,
        140,
        93,
        75
      ]
    },
    {
      name: "UserVolumeAccumulator",
      discriminator: [
        86,
        255,
        112,
        14,
        102,
        53,
        154,
        250
      ]
    }
  ],
  events: [
    {
      name: "AdminCtoPoolEvent",
      discriminator: [
        47,
        35,
        163,
        249,
        150,
        157,
        147,
        122
      ]
    },
    {
      name: "AdminUpdateTokenIncentivesEvent",
      discriminator: [
        147,
        250,
        108,
        120,
        247,
        29,
        67,
        222
      ]
    },
    {
      name: "BoostBuyAndBurnEvent",
      discriminator: [
        63,
        69,
        28,
        22,
        48,
        92,
        194,
        185
      ]
    },
    {
      name: "BuyEvent",
      discriminator: [
        103,
        244,
        82,
        31,
        44,
        245,
        119,
        119
      ]
    },
    {
      name: "ClaimCashbackEvent",
      discriminator: [
        226,
        214,
        246,
        33,
        7,
        242,
        147,
        229
      ]
    },
    {
      name: "ClaimTokenIncentivesEvent",
      discriminator: [
        79,
        172,
        246,
        49,
        205,
        91,
        206,
        232
      ]
    },
    {
      name: "CloseUserVolumeAccumulatorEvent",
      discriminator: [
        146,
        159,
        189,
        172,
        146,
        88,
        56,
        244
      ]
    },
    {
      name: "CollectCoinCreatorFeeEvent",
      discriminator: [
        232,
        245,
        194,
        238,
        234,
        218,
        58,
        89
      ]
    },
    {
      name: "CreateConfigEvent",
      discriminator: [
        107,
        52,
        89,
        129,
        55,
        226,
        81,
        22
      ]
    },
    {
      name: "CreatePoolEvent",
      discriminator: [
        177,
        49,
        12,
        210,
        160,
        118,
        167,
        116
      ]
    },
    {
      name: "DepositEvent",
      discriminator: [
        120,
        248,
        61,
        83,
        31,
        142,
        107,
        144
      ]
    },
    {
      name: "DisableEvent",
      discriminator: [
        107,
        253,
        193,
        76,
        228,
        202,
        27,
        104
      ]
    },
    {
      name: "ExtendAccountEvent",
      discriminator: [
        97,
        97,
        215,
        144,
        93,
        146,
        22,
        124
      ]
    },
    {
      name: "InitBoostEvent",
      discriminator: [
        174,
        124,
        74,
        249,
        4,
        81,
        246,
        17
      ]
    },
    {
      name: "InitUserVolumeAccumulatorEvent",
      discriminator: [
        134,
        36,
        13,
        72,
        232,
        101,
        130,
        216
      ]
    },
    {
      name: "MigratePoolCoinCreatorEvent",
      discriminator: [
        170,
        221,
        82,
        199,
        147,
        165,
        247,
        46
      ]
    },
    {
      name: "ReservedFeeRecipientsEvent",
      discriminator: [
        43,
        188,
        250,
        18,
        221,
        75,
        187,
        95
      ]
    },
    {
      name: "SellEvent",
      discriminator: [
        62,
        47,
        55,
        10,
        165,
        3,
        220,
        42
      ]
    },
    {
      name: "SetBondingCurveCoinCreatorEvent",
      discriminator: [
        242,
        231,
        235,
        102,
        65,
        99,
        189,
        211
      ]
    },
    {
      name: "SetBoostAuthorityEvent",
      discriminator: [
        89,
        128,
        240,
        141,
        91,
        202,
        71,
        105
      ]
    },
    {
      name: "SetMetaplexCoinCreatorEvent",
      discriminator: [
        150,
        107,
        199,
        123,
        124,
        207,
        102,
        228
      ]
    },
    {
      name: "SyncUserVolumeAccumulatorEvent",
      discriminator: [
        197,
        122,
        167,
        124,
        116,
        81,
        91,
        255
      ]
    },
    {
      name: "UpdateAdminEvent",
      discriminator: [
        225,
        152,
        171,
        87,
        246,
        63,
        66,
        234
      ]
    },
    {
      name: "UpdateCreatorFeeConfigEvent",
      discriminator: [
        152,
        198,
        124,
        124,
        106,
        246,
        127,
        191
      ]
    },
    {
      name: "UpdateFeeConfigEvent",
      discriminator: [
        90,
        23,
        65,
        35,
        62,
        244,
        188,
        208
      ]
    },
    {
      name: "WithdrawEvent",
      discriminator: [
        22,
        9,
        133,
        26,
        160,
        44,
        71,
        192
      ]
    }
  ],
  errors: [
    {
      code: 6e3,
      name: "FeeBasisPointsExceedsMaximum"
    },
    {
      code: 6001,
      name: "ZeroBaseAmount"
    },
    {
      code: 6002,
      name: "ZeroQuoteAmount"
    },
    {
      code: 6003,
      name: "TooLittlePoolTokenLiquidity"
    },
    {
      code: 6004,
      name: "ExceededSlippage"
    },
    {
      code: 6005,
      name: "InvalidAdmin"
    },
    {
      code: 6006,
      name: "UnsupportedBaseMint"
    },
    {
      code: 6007,
      name: "UnsupportedQuoteMint"
    },
    {
      code: 6008,
      name: "InvalidBaseMint"
    },
    {
      code: 6009,
      name: "InvalidQuoteMint"
    },
    {
      code: 6010,
      name: "InvalidLpMint"
    },
    {
      code: 6011,
      name: "AllProtocolFeeRecipientsShouldBeNonZero"
    },
    {
      code: 6012,
      name: "UnsortedNotUniqueProtocolFeeRecipients"
    },
    {
      code: 6013,
      name: "InvalidProtocolFeeRecipient"
    },
    {
      code: 6014,
      name: "InvalidPoolBaseTokenAccount"
    },
    {
      code: 6015,
      name: "InvalidPoolQuoteTokenAccount"
    },
    {
      code: 6016,
      name: "BuyMoreBaseAmountThanPoolReserves"
    },
    {
      code: 6017,
      name: "DisabledCreatePool"
    },
    {
      code: 6018,
      name: "DisabledDeposit"
    },
    {
      code: 6019,
      name: "DisabledWithdraw"
    },
    {
      code: 6020,
      name: "DisabledBuy"
    },
    {
      code: 6021,
      name: "DisabledSell"
    },
    {
      code: 6022,
      name: "SameMint"
    },
    {
      code: 6023,
      name: "Overflow"
    },
    {
      code: 6024,
      name: "Truncation"
    },
    {
      code: 6025,
      name: "DivisionByZero"
    },
    {
      code: 6026,
      name: "NewSizeLessThanCurrentSize"
    },
    {
      code: 6027,
      name: "AccountTypeNotSupported"
    },
    {
      code: 6028,
      name: "OnlyCanonicalPumpPoolsCanHaveCoinCreator"
    },
    {
      code: 6029,
      name: "InvalidAdminSetCoinCreatorAuthority"
    },
    {
      code: 6030,
      name: "StartTimeInThePast"
    },
    {
      code: 6031,
      name: "EndTimeInThePast"
    },
    {
      code: 6032,
      name: "EndTimeBeforeStartTime"
    },
    {
      code: 6033,
      name: "TimeRangeTooLarge"
    },
    {
      code: 6034,
      name: "EndTimeBeforeCurrentDay"
    },
    {
      code: 6035,
      name: "SupplyUpdateForFinishedRange"
    },
    {
      code: 6036,
      name: "DayIndexAfterEndIndex"
    },
    {
      code: 6037,
      name: "DayInActiveRange"
    },
    {
      code: 6038,
      name: "InvalidIncentiveMint"
    },
    {
      code: 6039,
      name: "BuyNotEnoughQuoteTokensToCoverFees",
      msg: "buy: Not enough quote tokens to cover for fees."
    },
    {
      code: 6040,
      name: "BuySlippageBelowMinBaseAmountOut",
      msg: "buy: slippage - would buy less tokens than expected min_base_amount_out"
    },
    {
      code: 6041,
      name: "MayhemModeDisabled"
    },
    {
      code: 6042,
      name: "OnlyPumpPoolsMayhemMode"
    },
    {
      code: 6043,
      name: "MayhemModeInDesiredState"
    },
    {
      code: 6044,
      name: "NotEnoughRemainingAccounts"
    },
    {
      code: 6045,
      name: "InvalidSharingConfigBaseMint"
    },
    {
      code: 6046,
      name: "InvalidSharingConfigCoinCreator"
    },
    {
      code: 6047,
      name: "CoinCreatorMigratedToSharingConfig",
      msg: "coin creator has been migrated to sharing config"
    },
    {
      code: 6048,
      name: "CreatorVaultMigratedToSharingConfig",
      msg: "creator_vault has been migrated to sharing config, use pump:distribute_creator_fees instead"
    },
    {
      code: 6049,
      name: "CashbackNotEnabled",
      msg: "Cashback is disabled"
    },
    {
      code: 6050,
      name: "OnlyPumpPoolsCashback"
    },
    {
      code: 6051,
      name: "CashbackNotInDesiredState"
    },
    {
      code: 6052,
      name: "TokensInVaultLessThanCashbackEarned"
    },
    {
      code: 6053,
      name: "BuybackFeeRecipientNotAuthorized",
      msg: "Buyback fee recipient not authorized"
    },
    {
      code: 6054,
      name: "AllBuybackFeeRecipientsShouldBeNonZero"
    },
    {
      code: 6055,
      name: "NotUniqueBuybackFeeRecipients"
    },
    {
      code: 6056,
      name: "BuybackBasisPointsOutOfRange",
      msg: "buyback_basis_points must be <= 10_000"
    },
    {
      code: 6057,
      name: "WrongBuybackFeeRecipientsCount",
      msg: "buyback fee recipients require exactly 8 remaining accounts (or none)"
    },
    {
      code: 6058,
      name: "BuybackFeeRecipientMissing"
    },
    {
      code: 6059,
      name: "MissingCashbackAccounts",
      msg: "Cashback trade is missing the required remaining accounts"
    },
    {
      code: 6060,
      name: "InvalidCashbackAccumulator",
      msg: "Cashback user_volume_accumulator account is invalid"
    },
    {
      code: 6061,
      name: "InvalidCashbackAccumulatorAta",
      msg: "Cashback user_volume_accumulator ATA is missing or invalid"
    },
    {
      code: 6062,
      name: "InvalidPoolV2",
      msg: "pool_v2 remaining account is missing or invalid"
    },
    {
      code: 6063,
      name: "InsufficientRealQuoteReserves",
      msg: "BOOST: sell output exceeds the real quote vault. effective = real + virtual is pricing-only; payout is capped at real_vault, so quote min(out, real_vault)"
    },
    {
      code: 6064,
      name: "BoostPoolLiquidityUnsupported",
      msg: "BOOST: deposit/withdraw don't apply to boost pools"
    },
    {
      code: 6065,
      name: "PoolCannotBoost",
      msg: "BOOST: pool cannot be boosted (no virtual reserves)"
    },
    {
      code: 6066,
      name: "BoostDisabled",
      msg: "BOOST: boost is disabled"
    },
    {
      code: 6067,
      name: "SeedLockViolation",
      msg: "BOOST: lp_supply must never drop below the circulating LP mint supply"
    },
    {
      code: 6068,
      name: "CreatorFeeNotConfigurable",
      msg: "Configurable creator fee is disabled"
    },
    {
      code: 6069,
      name: "CreatorFeeBpsOutOfRange",
      msg: "Creator fee basis points must be between 1 and the configured maximum"
    },
    {
      code: 6070,
      name: "CreatorFeeNotEditable",
      msg: "Creator fee is not editable for this pool"
    },
    {
      code: 6071,
      name: "CreatorFeeNotAllowedForCashbackCoin",
      msg: "Cashback coins cannot have a creator fee"
    },
    {
      code: 6072,
      name: "SharingConfigNotActive",
      msg: "Sharing config is not active"
    },
    {
      code: 6073,
      name: "NotAuthorized",
      msg: "Not authorized"
    },
    {
      code: 6074,
      name: "HolderRewardCreatorImmutable",
      msg: "The coin creator of a holder-reward pool cannot be changed"
    },
    {
      code: 6075,
      name: "CtoNotAllowedForMayhemPool",
      msg: "CTO is not allowed on a mayhem-mode pool"
    },
    {
      code: 6076,
      name: "InvalidHolderRewardCoinCreator",
      msg: "A holder-reward pool's coin creator must be the holder-rewards PDA"
    },
    {
      code: 6077,
      name: "CreatorFeeNotConfigurableForQuote",
      msg: "Creator fee is not configurable on a SOL or USDC quote; the fee schedule applies"
    }
  ],
  types: [
    {
      name: "AdminCtoPoolEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "old_coin_creator",
            type: "pubkey"
          },
          {
            name: "new_coin_creator",
            type: "pubkey"
          },
          {
            name: "is_holder_reward",
            type: "bool"
          },
          {
            name: "is_cashback_coin",
            type: "bool"
          },
          {
            name: "old_creator_fee_bps",
            type: "u64"
          },
          {
            name: "new_creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "AdminUpdateTokenIncentivesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "start_time",
            type: "i64"
          },
          {
            name: "end_time",
            type: "i64"
          },
          {
            name: "day_number",
            type: "u64"
          },
          {
            name: "token_supply_per_day",
            type: "u64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "seconds_in_a_day",
            type: "i64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "BondingCurve",
      type: {
        kind: "struct",
        fields: [
          {
            name: "virtual_token_reserves",
            type: "u64"
          },
          {
            name: "virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "real_token_reserves",
            type: "u64"
          },
          {
            name: "real_sol_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "complete",
            type: "bool"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          },
          {
            name: "is_cashback_coin",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "BoostBuyAndBurnEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "quote_amount_in_requested",
            type: "u64"
          },
          {
            name: "quote_amount_in_used",
            type: "u64"
          },
          {
            name: "base_amount_burned",
            type: "u64"
          },
          {
            name: "virtual_quote_reserves",
            type: "i128"
          },
          {
            name: "real_quote_reserves_after",
            type: "u64"
          },
          {
            name: "base_reserves_after",
            type: "u64"
          },
          {
            name: "boost_vault_remaining",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "BuyEvent",
      docs: [
        'ix_name: "buy" | "buy_exact_quote_in"'
      ],
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "base_amount_out",
            type: "u64"
          },
          {
            name: "max_quote_amount_in",
            type: "u64"
          },
          {
            name: "user_base_token_reserves",
            type: "u64"
          },
          {
            name: "user_quote_token_reserves",
            type: "u64"
          },
          {
            name: "pool_base_token_reserves",
            type: "u64"
          },
          {
            name: "pool_quote_token_reserves",
            type: "u64"
          },
          {
            name: "quote_amount_in",
            type: "u64"
          },
          {
            name: "lp_fee_basis_points",
            type: "u64"
          },
          {
            name: "lp_fee",
            type: "u64"
          },
          {
            name: "protocol_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee",
            type: "u64"
          },
          {
            name: "quote_amount_in_with_lp_fee",
            type: "u64"
          },
          {
            name: "user_quote_amount_in",
            type: "u64"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "user_base_token_account",
            type: "pubkey"
          },
          {
            name: "user_quote_token_account",
            type: "pubkey"
          },
          {
            name: "protocol_fee_recipient",
            type: "pubkey"
          },
          {
            name: "protocol_fee_recipient_token_account",
            type: "pubkey"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          },
          {
            name: "coin_creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "coin_creator_fee",
            type: "u64"
          },
          {
            name: "track_volume",
            type: "bool"
          },
          {
            name: "total_unclaimed_tokens",
            type: "u64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          },
          {
            name: "last_update_timestamp",
            type: "i64"
          },
          {
            name: "min_base_amount_out",
            type: "u64"
          },
          {
            name: "ix_name",
            type: "string"
          },
          {
            name: "cashback_fee_basis_points",
            type: "u64"
          },
          {
            name: "cashback",
            type: "u64"
          },
          {
            name: "buyback_fee_basis_points",
            type: "u64"
          },
          {
            name: "buyback_fee",
            type: "u64"
          },
          {
            name: "virtual_quote_reserves",
            type: "i128"
          },
          {
            name: "can_boost",
            type: "bool"
          },
          {
            name: "base_supply",
            type: "u64"
          },
          {
            name: "holder_rewards_bps",
            type: "u64"
          },
          {
            name: "holder_rewards",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "ClaimCashbackEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "amount",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "total_claimed",
            type: "u64"
          },
          {
            name: "total_cashback_earned",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "ClaimTokenIncentivesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "amount",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "CloseUserVolumeAccumulatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "total_unclaimed_tokens",
            type: "u64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          },
          {
            name: "last_update_timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "CollectCoinCreatorFeeEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          },
          {
            name: "coin_creator_fee",
            type: "u64"
          },
          {
            name: "coin_creator_vault_ata",
            type: "pubkey"
          },
          {
            name: "coin_creator_token_account",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "ConfigStatus",
      type: {
        kind: "enum",
        variants: [
          {
            name: "Paused"
          },
          {
            name: "Active"
          }
        ]
      }
    },
    {
      name: "CreateConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "lp_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee_recipients",
            type: {
              array: [
                "pubkey",
                8
              ]
            }
          },
          {
            name: "coin_creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "admin_set_coin_creator_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "CreatePoolEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "index",
            type: "u16"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "base_mint_decimals",
            type: "u8"
          },
          {
            name: "quote_mint_decimals",
            type: "u8"
          },
          {
            name: "base_amount_in",
            type: "u64"
          },
          {
            name: "quote_amount_in",
            type: "u64"
          },
          {
            name: "pool_base_amount",
            type: "u64"
          },
          {
            name: "pool_quote_amount",
            type: "u64"
          },
          {
            name: "minimum_liquidity",
            type: "u64"
          },
          {
            name: "initial_liquidity",
            type: "u64"
          },
          {
            name: "lp_token_amount_out",
            type: "u64"
          },
          {
            name: "pool_bump",
            type: "u8"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "lp_mint",
            type: "pubkey"
          },
          {
            name: "user_base_token_account",
            type: "pubkey"
          },
          {
            name: "user_quote_token_account",
            type: "pubkey"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          },
          {
            name: "can_edit_creator_fee",
            type: "bool"
          },
          {
            name: "is_holder_reward",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "DepositEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "lp_token_amount_out",
            type: "u64"
          },
          {
            name: "max_base_amount_in",
            type: "u64"
          },
          {
            name: "max_quote_amount_in",
            type: "u64"
          },
          {
            name: "user_base_token_reserves",
            type: "u64"
          },
          {
            name: "user_quote_token_reserves",
            type: "u64"
          },
          {
            name: "pool_base_token_reserves",
            type: "u64"
          },
          {
            name: "pool_quote_token_reserves",
            type: "u64"
          },
          {
            name: "base_amount_in",
            type: "u64"
          },
          {
            name: "quote_amount_in",
            type: "u64"
          },
          {
            name: "lp_mint_supply",
            type: "u64"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "user_base_token_account",
            type: "pubkey"
          },
          {
            name: "user_quote_token_account",
            type: "pubkey"
          },
          {
            name: "user_pool_token_account",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "DisableEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "disable_create_pool",
            type: "bool"
          },
          {
            name: "disable_deposit",
            type: "bool"
          },
          {
            name: "disable_withdraw",
            type: "bool"
          },
          {
            name: "disable_buy",
            type: "bool"
          },
          {
            name: "disable_sell",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "ExtendAccountEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "account",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "current_size",
            type: "u64"
          },
          {
            name: "new_size",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "FeeConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          },
          {
            name: "fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "stable_fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "exotic_flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "FeeTier",
      type: {
        kind: "struct",
        fields: [
          {
            name: "market_cap_lamports_threshold",
            type: "u128"
          },
          {
            name: "fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "Fees",
      type: {
        kind: "struct",
        fields: [
          {
            name: "lp_fee_bps",
            type: "u64"
          },
          {
            name: "protocol_fee_bps",
            type: "u64"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "GlobalConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "admin",
            docs: [
              "The admin pubkey"
            ],
            type: "pubkey"
          },
          {
            name: "lp_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee_basis_points",
            type: "u64"
          },
          {
            name: "disable_flags",
            docs: [
              "Flags to disable certain functionality",
              "bit 0 - Disable create pool",
              "bit 1 - Disable deposit",
              "bit 2 - Disable withdraw",
              "bit 3 - Disable buy",
              "bit 4 - Disable sell"
            ],
            type: "u8"
          },
          {
            name: "protocol_fee_recipients",
            docs: [
              "Addresses of the protocol fee recipients"
            ],
            type: {
              array: [
                "pubkey",
                8
              ]
            }
          },
          {
            name: "coin_creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "admin_set_coin_creator_authority",
            docs: [
              "The admin authority for setting coin creators"
            ],
            type: "pubkey"
          },
          {
            name: "whitelist_pda",
            type: "pubkey"
          },
          {
            name: "reserved_fee_recipient",
            type: "pubkey"
          },
          {
            name: "mayhem_mode_enabled",
            type: "bool"
          },
          {
            name: "reserved_fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          },
          {
            name: "is_cashback_enabled",
            type: "bool"
          },
          {
            name: "buyback_fee_recipients",
            type: {
              array: [
                "pubkey",
                8
              ]
            }
          },
          {
            name: "buyback_basis_points",
            type: "u64"
          },
          {
            name: "boost_authority",
            type: "pubkey"
          },
          {
            name: "boost_enabled",
            type: "bool"
          },
          {
            name: "creator_fee_configurable",
            type: "bool"
          },
          {
            name: "max_configurable_creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "GlobalVolumeAccumulator",
      type: {
        kind: "struct",
        fields: [
          {
            name: "start_time",
            type: "i64"
          },
          {
            name: "end_time",
            type: "i64"
          },
          {
            name: "seconds_in_a_day",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "total_token_supply",
            type: {
              array: [
                "u64",
                30
              ]
            }
          },
          {
            name: "sol_volumes",
            type: {
              array: [
                "u64",
                30
              ]
            }
          }
        ]
      }
    },
    {
      name: "InitBoostEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "virtual_quote_reserves",
            type: "i128"
          },
          {
            name: "real_quote_reserves_after",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "InitUserVolumeAccumulatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "payer",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "MigratePoolCoinCreatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "sharing_config",
            type: "pubkey"
          },
          {
            name: "old_coin_creator",
            type: "pubkey"
          },
          {
            name: "new_coin_creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "OptionBool",
      type: {
        kind: "struct",
        fields: [
          "bool"
        ]
      }
    },
    {
      name: "OptionU64",
      type: {
        kind: "struct",
        fields: [
          "u64"
        ]
      }
    },
    {
      name: "Pool",
      type: {
        kind: "struct",
        fields: [
          {
            name: "pool_bump",
            type: "u8"
          },
          {
            name: "index",
            type: "u16"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "lp_mint",
            type: "pubkey"
          },
          {
            name: "pool_base_token_account",
            type: "pubkey"
          },
          {
            name: "pool_quote_token_account",
            type: "pubkey"
          },
          {
            name: "lp_supply",
            docs: [
              "True circulating supply without burns and lock-ups"
            ],
            type: "u64"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          },
          {
            name: "is_cashback_coin",
            type: "bool"
          },
          {
            name: "virtual_quote_reserves",
            docs: [
              "For non-boost pools, value is 0, so the behavior is identical to legacy pools."
            ],
            type: "i128"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          },
          {
            name: "can_edit_creator_fee",
            type: "bool"
          },
          {
            name: "is_holder_reward",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "ReservedFeeRecipientsEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "reserved_fee_recipient",
            type: "pubkey"
          },
          {
            name: "reserved_fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          }
        ]
      }
    },
    {
      name: "SellEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "base_amount_in",
            type: "u64"
          },
          {
            name: "min_quote_amount_out",
            type: "u64"
          },
          {
            name: "user_base_token_reserves",
            type: "u64"
          },
          {
            name: "user_quote_token_reserves",
            type: "u64"
          },
          {
            name: "pool_base_token_reserves",
            type: "u64"
          },
          {
            name: "pool_quote_token_reserves",
            type: "u64"
          },
          {
            name: "quote_amount_out",
            type: "u64"
          },
          {
            name: "lp_fee_basis_points",
            type: "u64"
          },
          {
            name: "lp_fee",
            type: "u64"
          },
          {
            name: "protocol_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee",
            type: "u64"
          },
          {
            name: "quote_amount_out_without_lp_fee",
            type: "u64"
          },
          {
            name: "user_quote_amount_out",
            type: "u64"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "user_base_token_account",
            type: "pubkey"
          },
          {
            name: "user_quote_token_account",
            type: "pubkey"
          },
          {
            name: "protocol_fee_recipient",
            type: "pubkey"
          },
          {
            name: "protocol_fee_recipient_token_account",
            type: "pubkey"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          },
          {
            name: "coin_creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "coin_creator_fee",
            type: "u64"
          },
          {
            name: "cashback_fee_basis_points",
            type: "u64"
          },
          {
            name: "cashback",
            type: "u64"
          },
          {
            name: "buyback_fee_basis_points",
            type: "u64"
          },
          {
            name: "buyback_fee",
            type: "u64"
          },
          {
            name: "virtual_quote_reserves",
            type: "i128"
          },
          {
            name: "can_boost",
            type: "bool"
          },
          {
            name: "base_supply",
            type: "u64"
          },
          {
            name: "holder_rewards_bps",
            type: "u64"
          },
          {
            name: "holder_rewards",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "SetBondingCurveCoinCreatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SetBoostAuthorityEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "old_boost_authority",
            type: "pubkey"
          },
          {
            name: "new_boost_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SetMetaplexCoinCreatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "metadata",
            type: "pubkey"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "Shareholder",
      type: {
        kind: "struct",
        fields: [
          {
            name: "address",
            type: "pubkey"
          },
          {
            name: "share_bps",
            type: "u16"
          }
        ]
      }
    },
    {
      name: "SharingConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "version",
            type: "u8"
          },
          {
            name: "status",
            type: {
              defined: {
                name: "ConfigStatus"
              }
            }
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "admin_revoked",
            type: "bool"
          },
          {
            name: "shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          }
        ]
      }
    },
    {
      name: "SyncUserVolumeAccumulatorEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "total_claimed_tokens_before",
            type: "u64"
          },
          {
            name: "total_claimed_tokens_after",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "UpdateAdminEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "new_admin",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "UpdateCreatorFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "creator_fee_configurable",
            type: "bool"
          },
          {
            name: "max_configurable_creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "UpdateFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "lp_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee_basis_points",
            type: "u64"
          },
          {
            name: "protocol_fee_recipients",
            type: {
              array: [
                "pubkey",
                8
              ]
            }
          },
          {
            name: "coin_creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "admin_set_coin_creator_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "UserVolumeAccumulator",
      type: {
        kind: "struct",
        fields: [
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "needs_claim",
            type: "bool"
          },
          {
            name: "total_unclaimed_tokens",
            type: "u64"
          },
          {
            name: "total_claimed_tokens",
            type: "u64"
          },
          {
            name: "current_sol_volume",
            type: "u64"
          },
          {
            name: "last_update_timestamp",
            type: "i64"
          },
          {
            name: "has_total_claimed_tokens",
            type: "bool"
          },
          {
            name: "cashback_earned",
            type: "u64"
          },
          {
            name: "total_cashback_claimed",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "WithdrawEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "lp_token_amount_in",
            type: "u64"
          },
          {
            name: "min_base_amount_out",
            type: "u64"
          },
          {
            name: "min_quote_amount_out",
            type: "u64"
          },
          {
            name: "user_base_token_reserves",
            type: "u64"
          },
          {
            name: "user_quote_token_reserves",
            type: "u64"
          },
          {
            name: "pool_base_token_reserves",
            type: "u64"
          },
          {
            name: "pool_quote_token_reserves",
            type: "u64"
          },
          {
            name: "base_amount_out",
            type: "u64"
          },
          {
            name: "quote_amount_out",
            type: "u64"
          },
          {
            name: "lp_mint_supply",
            type: "u64"
          },
          {
            name: "pool",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "user_base_token_account",
            type: "pubkey"
          },
          {
            name: "user_quote_token_account",
            type: "pubkey"
          },
          {
            name: "user_pool_token_account",
            type: "pubkey"
          }
        ]
      }
    }
  ]
};

// src/idl/pump_fees.json
var pump_fees_default = {
  address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ",
  metadata: {
    name: "pump_fees",
    version: "0.1.0",
    spec: "0.1.0",
    description: "Created with Anchor"
  },
  instructions: [
    {
      name: "admin_cto_sharing_config",
      discriminator: [
        60,
        100,
        144,
        156,
        64,
        138,
        182,
        37
      ],
      accounts: [
        {
          name: "pool_authority",
          signer: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  112,
                  111,
                  111,
                  108,
                  45,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "authority",
          signer: true
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "sharing_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        }
      ],
      args: [
        {
          name: "new_admin",
          type: {
            option: "pubkey"
          }
        }
      ]
    },
    {
      name: "claim_social_fee_pda",
      discriminator: [
        225,
        21,
        251,
        133,
        161,
        30,
        199,
        226
      ],
      accounts: [
        {
          name: "recipient",
          writable: true
        },
        {
          name: "social_fee_pda",
          writable: true
        },
        {
          name: "fee_program_global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "social_claim_authority",
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "user_id",
          type: "string"
        },
        {
          name: "platform",
          type: "u8"
        }
      ],
      returns: {
        option: {
          defined: {
            name: "SocialFeePdaClaimed"
          }
        }
      }
    },
    {
      name: "claim_social_fee_pda_v2",
      discriminator: [
        17,
        77,
        240,
        134,
        58,
        188,
        53,
        149
      ],
      accounts: [
        {
          name: "recipient",
          writable: true
        },
        {
          name: "social_fee_pda",
          writable: true
        },
        {
          name: "quote_mint",
          docs: [
            "Quote mint for claim"
          ],
          writable: true
        },
        {
          name: "associated_social_fee_pda",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "social_fee_pda"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "associated_recipient",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "recipient"
              },
              {
                kind: "account",
                path: "quote_token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "quote_token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "fee_program_global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "social_claim_authority",
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "user_id",
          type: "string"
        },
        {
          name: "platform",
          type: "u8"
        }
      ],
      returns: {
        option: {
          defined: {
            name: "SocialFeePdaClaimed"
          }
        }
      }
    },
    {
      name: "crank_donation_fee_pda",
      discriminator: [
        220,
        10,
        189,
        167,
        169,
        17,
        25,
        69
      ],
      accounts: [
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "payer",
          docs: [
            "Pays rent when [`temp_wsol_token_account`] is created (`init_if_needed`); receives rent when it is closed after the relay CPI."
          ],
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "token_program",
          address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "rent",
          address: "SysvarRent111111111111111111111111111111111"
        },
        {
          name: "fee_program_global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "donation_fee_pda",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  100,
                  111,
                  110,
                  97,
                  116,
                  105,
                  111,
                  110,
                  45,
                  102,
                  101,
                  101,
                  45,
                  112,
                  100,
                  97
                ]
              },
              {
                kind: "account",
                path: "donation_fee_pda.base_mint",
                account: "DonationFeePda"
              },
              {
                kind: "account",
                path: "donation_fee_pda.config_id",
                account: "DonationFeePda"
              }
            ]
          }
        },
        {
          name: "quote_mint",
          docs: [
            "Quote mint from donation fee pda."
          ],
          writable: true
        },
        {
          name: "donation_fee_pda_ata",
          docs: [
            "WSOL ATA owned by `donation_fee_pda`."
          ],
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "donation_fee_pda"
              },
              {
                kind: "const",
                value: [
                  6,
                  221,
                  246,
                  225,
                  215,
                  101,
                  161,
                  147,
                  217,
                  203,
                  225,
                  70,
                  206,
                  235,
                  121,
                  172,
                  28,
                  180,
                  133,
                  237,
                  95,
                  91,
                  55,
                  145,
                  58,
                  140,
                  245,
                  133,
                  126,
                  255,
                  0,
                  169
                ]
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "donation_relay_program",
          address: "RLAYHr9TRFcKB2ubYQhspcnXiaGpaVzNQvHytt47RZu"
        },
        {
          name: "donation_relay_event_authority"
        },
        {
          name: "mint_whitelist"
        },
        {
          name: "epoch_tracker",
          writable: true
        },
        {
          name: "debouncer",
          writable: true
        },
        {
          name: "debouncer_ata",
          writable: true
        }
      ],
      args: []
    },
    {
      name: "create_donation_fee_pda",
      discriminator: [
        244,
        139,
        16,
        88,
        14,
        255,
        122,
        26
      ],
      accounts: [
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "fee_program_global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "donation_fee_pda",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  100,
                  111,
                  110,
                  97,
                  116,
                  105,
                  111,
                  110,
                  45,
                  102,
                  101,
                  101,
                  45,
                  112,
                  100,
                  97
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              },
              {
                kind: "account",
                path: "config_id"
              }
            ]
          }
        },
        {
          name: "config_id",
          docs: [
            "stored on the PDA, so distinct `config_id`s for the same `base_mint` derive distinct addresses."
          ]
        },
        {
          name: "base_mint"
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pool"
        },
        {
          name: "sharing_config",
          docs: [
            "(derived from `[SHARING_CONFIG_SEED, base_mint]`)"
          ],
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "base_mint"
              }
            ]
          }
        }
      ],
      args: []
    },
    {
      name: "create_fee_sharing_config",
      docs: [
        "Create Fee Sharing Config"
      ],
      discriminator: [
        195,
        78,
        86,
        76,
        111,
        52,
        251,
        213
      ],
      accounts: [
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "mint"
        },
        {
          name: "sharing_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "bonding_curve",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "pump_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pool",
          writable: true,
          optional: true
        },
        {
          name: "pump_amm_program",
          optional: true,
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "pump_amm_event_authority",
          optional: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                20,
                222,
                252,
                130,
                94,
                198,
                118,
                148,
                37,
                8,
                24,
                187,
                101,
                64,
                101,
                244,
                41,
                141,
                49,
                86,
                213,
                113,
                180,
                212,
                248,
                9,
                12,
                24,
                233,
                168,
                99
              ]
            }
          }
        }
      ],
      args: []
    },
    {
      name: "create_social_fee_pda",
      discriminator: [
        144,
        224,
        59,
        211,
        78,
        248,
        202,
        220
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "social_fee_pda",
          writable: true
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "fee_program_global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "user_id",
          type: "string"
        },
        {
          name: "platform",
          type: "u8"
        }
      ]
    },
    {
      name: "extend_fee_config",
      docs: [
        "Realloc the fee_config PDA to [`FeeConfig::CURRENT_SIZE`] (signer pays rent delta)."
      ],
      discriminator: [
        68,
        179,
        244,
        90,
        173,
        56,
        17,
        217
      ],
      accounts: [
        {
          name: "fee_config",
          writable: true
        },
        {
          name: "user",
          signer: true
        },
        {
          name: "config_program_id"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "get_fees",
      docs: [
        "Get Fees"
      ],
      discriminator: [
        231,
        37,
        126,
        85,
        207,
        91,
        63,
        52
      ],
      accounts: [
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "config_program_id"
        }
      ],
      args: [
        {
          name: "is_pump_pool",
          type: "bool"
        },
        {
          name: "market_cap_lamports",
          type: "u128"
        },
        {
          name: "trade_size_lamports",
          type: "u64"
        },
        {
          name: "is_new_quote_mint",
          type: {
            defined: {
              name: "OptionBool"
            }
          }
        }
      ],
      returns: {
        defined: {
          name: "Fees"
        }
      }
    },
    {
      name: "get_fees_with_quote_mint",
      discriminator: [
        154,
        237,
        138,
        92,
        162,
        2,
        162,
        187
      ],
      accounts: [
        {
          name: "fee_config",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "config_program_id"
        }
      ],
      args: [
        {
          name: "is_pump_pool",
          type: "bool"
        },
        {
          name: "market_cap_lamports",
          type: "u128"
        },
        {
          name: "quote_mint",
          type: "pubkey"
        }
      ],
      returns: {
        defined: {
          name: "Fees"
        }
      }
    },
    {
      name: "initialize_buyback",
      discriminator: [
        250,
        129,
        236,
        160,
        227,
        36,
        103,
        134
      ],
      accounts: [
        {
          name: "payer",
          writable: true,
          signer: true
        },
        {
          name: "buyback_vault",
          writable: true
        },
        {
          name: "buyback_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "buyback_vault"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "mint"
        },
        {
          name: "token_program"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "index",
          type: "u8"
        }
      ]
    },
    {
      name: "initialize_fee_config",
      docs: [
        "Initialize FeeConfig admin"
      ],
      discriminator: [
        62,
        162,
        20,
        133,
        121,
        65,
        145,
        27
      ],
      accounts: [
        {
          name: "admin",
          writable: true,
          signer: true,
          address: "8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8"
        },
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "config_program_id"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "initialize_fee_program_global",
      discriminator: [
        35,
        215,
        130,
        84,
        233,
        56,
        124,
        167
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "pump_global"
          ]
        },
        {
          name: "pump_global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "social_claim_authority",
          type: "pubkey"
        },
        {
          name: "disable_flags",
          type: "u8"
        },
        {
          name: "claim_rate_limit",
          type: "u64"
        }
      ]
    },
    {
      name: "revoke_fee_sharing_authority",
      docs: [
        "Revoke Fee Sharing Authority"
      ],
      discriminator: [
        18,
        233,
        158,
        39,
        185,
        207,
        58,
        104
      ],
      accounts: [],
      args: []
    },
    {
      name: "set_authority",
      discriminator: [
        133,
        250,
        37,
        21,
        110,
        163,
        26,
        121
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "new_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "set_claim_rate_limit",
      discriminator: [
        185,
        211,
        159,
        174,
        212,
        49,
        88,
        4
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "claim_rate_limit",
          type: "u64"
        }
      ]
    },
    {
      name: "set_disable_flags",
      discriminator: [
        194,
        217,
        112,
        35,
        114,
        222,
        51,
        190
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "disable_flags",
          type: "u8"
        }
      ]
    },
    {
      name: "set_exotic_flat_fees",
      discriminator: [
        30,
        234,
        149,
        138,
        252,
        230,
        39,
        73
      ],
      accounts: [
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "admin",
          writable: true,
          signer: true,
          relations: [
            "fee_config"
          ]
        },
        {
          name: "config_program_id"
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "exotic_flat_fees",
          type: {
            defined: {
              name: "Fees"
            }
          }
        }
      ]
    },
    {
      name: "set_social_claim_authority",
      discriminator: [
        147,
        54,
        184,
        154,
        136,
        237,
        185,
        153
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "social_claim_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "sweep_buyback",
      discriminator: [
        138,
        33,
        204,
        38,
        207,
        161,
        159,
        226
      ],
      accounts: [
        {
          name: "destination",
          writable: true
        },
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "buyback_vault"
          ]
        },
        {
          name: "buyback_vault",
          writable: true
        },
        {
          name: "buyback_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "buyback_vault"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "destination_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "destination"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                140,
                151,
                37,
                143,
                78,
                36,
                137,
                241,
                187,
                61,
                16,
                41,
                20,
                142,
                13,
                131,
                11,
                90,
                19,
                153,
                218,
                255,
                16,
                132,
                4,
                142,
                123,
                216,
                219,
                233,
                248,
                89
              ]
            }
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "mint"
        },
        {
          name: "token_program"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "index",
          type: "u8"
        }
      ]
    },
    {
      name: "transfer_fee_sharing_authority",
      docs: [
        "Transfer Fee Sharing Authority"
      ],
      discriminator: [
        202,
        10,
        75,
        200,
        164,
        34,
        210,
        96
      ],
      accounts: [],
      args: []
    },
    {
      name: "update_admin",
      docs: [
        "Update admin (only callable by admin)"
      ],
      discriminator: [
        161,
        176,
        40,
        213,
        60,
        184,
        179,
        228
      ],
      accounts: [
        {
          name: "admin",
          signer: true,
          relations: [
            "fee_config"
          ]
        },
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "new_admin"
        },
        {
          name: "config_program_id"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: []
    },
    {
      name: "update_buyback_authority",
      discriminator: [
        66,
        98,
        113,
        202,
        121,
        37,
        219,
        107
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "buyback_vault",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "index",
          type: "u8"
        },
        {
          name: "new_authority",
          type: "pubkey"
        }
      ]
    },
    {
      name: "update_buyback_claim_rate_limit",
      discriminator: [
        186,
        95,
        135,
        190,
        255,
        199,
        137,
        170
      ],
      accounts: [
        {
          name: "authority",
          writable: true,
          signer: true,
          relations: [
            "fee_program_global"
          ]
        },
        {
          name: "fee_program_global",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  45,
                  112,
                  114,
                  111,
                  103,
                  114,
                  97,
                  109,
                  45,
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ]
          }
        },
        {
          name: "buyback_vault",
          writable: true
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "index",
          type: "u8"
        },
        {
          name: "claim_rate_limit",
          type: "i64"
        }
      ]
    },
    {
      name: "update_fee_config",
      docs: [
        "Set/Replace fee parameters entirely (only callable by admin)"
      ],
      discriminator: [
        104,
        184,
        103,
        242,
        88,
        151,
        107,
        20
      ],
      accounts: [
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "admin",
          signer: true,
          relations: [
            "fee_config"
          ]
        },
        {
          name: "config_program_id"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "fee_tiers",
          type: {
            vec: {
              defined: {
                name: "FeeTier"
              }
            }
          }
        },
        {
          name: "flat_fees",
          type: {
            defined: {
              name: "Fees"
            }
          }
        }
      ]
    },
    {
      name: "update_fee_shares",
      docs: [
        "Update Fee Shares, make sure to distribute all the fees before calling this"
      ],
      discriminator: [
        189,
        13,
        136,
        99,
        187,
        164,
        237,
        35
      ],
      accounts: [
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "authority",
          signer: true
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "sharing_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "sharing_config"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "pump_program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "pump_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_amm_program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "amm_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                20,
                222,
                252,
                130,
                94,
                198,
                118,
                148,
                37,
                8,
                24,
                187,
                101,
                64,
                101,
                244,
                41,
                141,
                49,
                86,
                213,
                113,
                180,
                212,
                248,
                9,
                12,
                24,
                233,
                168,
                99
              ]
            }
          }
        },
        {
          name: "wsol_mint",
          address: "So11111111111111111111111111111111111111112"
        },
        {
          name: "token_program",
          address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "coin_creator_vault_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "sharing_config"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                20,
                222,
                252,
                130,
                94,
                198,
                118,
                148,
                37,
                8,
                24,
                187,
                101,
                64,
                101,
                244,
                41,
                141,
                49,
                86,
                213,
                113,
                180,
                212,
                248,
                9,
                12,
                24,
                233,
                168,
                99
              ]
            }
          }
        },
        {
          name: "coin_creator_vault_ata",
          writable: true
        }
      ],
      args: [
        {
          name: "shareholders",
          type: {
            vec: {
              defined: {
                name: "Shareholder"
              }
            }
          }
        }
      ]
    },
    {
      name: "update_fee_shares_v2",
      docs: [
        "Update Fee Shares, make sure to distribute all the fees before calling this"
      ],
      discriminator: [
        111,
        251,
        49,
        6,
        78,
        78,
        106,
        18
      ],
      accounts: [
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program",
          address: "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
        },
        {
          name: "authority",
          writable: true,
          signer: true
        },
        {
          name: "global",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  103,
                  108,
                  111,
                  98,
                  97,
                  108
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "mint",
          relations: [
            "sharing_config"
          ]
        },
        {
          name: "sharing_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  115,
                  104,
                  97,
                  114,
                  105,
                  110,
                  103,
                  45,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ]
          }
        },
        {
          name: "bonding_curve",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  98,
                  111,
                  110,
                  100,
                  105,
                  110,
                  103,
                  45,
                  99,
                  117,
                  114,
                  118,
                  101
                ]
              },
              {
                kind: "account",
                path: "mint"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_creator_vault",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  45,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "sharing_config"
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "pump_creator_vault"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        },
        {
          name: "system_program",
          address: "11111111111111111111111111111111"
        },
        {
          name: "pump_program",
          address: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        },
        {
          name: "pump_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                1,
                86,
                224,
                246,
                147,
                102,
                90,
                207,
                68,
                219,
                21,
                104,
                191,
                23,
                91,
                170,
                81,
                137,
                203,
                151,
                245,
                210,
                255,
                59,
                101,
                93,
                43,
                182,
                253,
                109,
                24,
                176
              ]
            }
          }
        },
        {
          name: "pump_amm_program",
          address: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        },
        {
          name: "amm_event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                20,
                222,
                252,
                130,
                94,
                198,
                118,
                148,
                37,
                8,
                24,
                187,
                101,
                64,
                101,
                244,
                41,
                141,
                49,
                86,
                213,
                113,
                180,
                212,
                248,
                9,
                12,
                24,
                233,
                168,
                99
              ]
            }
          }
        },
        {
          name: "quote_mint"
        },
        {
          name: "token_program"
        },
        {
          name: "associated_token_program",
          address: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        },
        {
          name: "coin_creator_vault_authority",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  99,
                  114,
                  101,
                  97,
                  116,
                  111,
                  114,
                  95,
                  118,
                  97,
                  117,
                  108,
                  116
                ]
              },
              {
                kind: "account",
                path: "sharing_config"
              }
            ],
            program: {
              kind: "const",
              value: [
                12,
                20,
                222,
                252,
                130,
                94,
                198,
                118,
                148,
                37,
                8,
                24,
                187,
                101,
                64,
                101,
                244,
                41,
                141,
                49,
                86,
                213,
                113,
                180,
                212,
                248,
                9,
                12,
                24,
                233,
                168,
                99
              ]
            }
          }
        },
        {
          name: "coin_creator_vault_ata",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "account",
                path: "coin_creator_vault_authority"
              },
              {
                kind: "account",
                path: "token_program"
              },
              {
                kind: "account",
                path: "quote_mint"
              }
            ],
            program: {
              kind: "account",
              path: "associated_token_program"
            }
          }
        }
      ],
      args: [
        {
          name: "shareholders",
          type: {
            vec: {
              defined: {
                name: "Shareholder"
              }
            }
          }
        }
      ]
    },
    {
      name: "update_stable_fee_config",
      docs: [
        "Set/Replace fee parameters entirely (only callable by admin)"
      ],
      discriminator: [
        107,
        169,
        100,
        179,
        134,
        155,
        146,
        221
      ],
      accounts: [
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "admin",
          signer: true,
          relations: [
            "fee_config"
          ]
        },
        {
          name: "config_program_id"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "fee_tiers",
          type: {
            vec: {
              defined: {
                name: "FeeTier"
              }
            }
          }
        }
      ]
    },
    {
      name: "upsert_fee_tiers",
      docs: [
        "Update or expand fee tiers (only callable by admin)"
      ],
      discriminator: [
        227,
        23,
        150,
        12,
        77,
        86,
        94,
        4
      ],
      accounts: [
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "admin",
          signer: true,
          relations: [
            "fee_config"
          ]
        },
        {
          name: "config_program_id"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "fee_tiers",
          type: {
            vec: {
              defined: {
                name: "FeeTier"
              }
            }
          }
        },
        {
          name: "offset",
          type: "u8"
        }
      ]
    },
    {
      name: "upsert_stable_fee_tiers",
      docs: [
        "Update or expand fee tiers (only callable by admin)"
      ],
      discriminator: [
        181,
        160,
        162,
        252,
        74,
        76,
        224,
        221
      ],
      accounts: [
        {
          name: "fee_config",
          writable: true,
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  102,
                  101,
                  101,
                  95,
                  99,
                  111,
                  110,
                  102,
                  105,
                  103
                ]
              },
              {
                kind: "account",
                path: "config_program_id"
              }
            ]
          }
        },
        {
          name: "admin",
          signer: true,
          relations: [
            "fee_config"
          ]
        },
        {
          name: "config_program_id"
        },
        {
          name: "event_authority",
          pda: {
            seeds: [
              {
                kind: "const",
                value: [
                  95,
                  95,
                  101,
                  118,
                  101,
                  110,
                  116,
                  95,
                  97,
                  117,
                  116,
                  104,
                  111,
                  114,
                  105,
                  116,
                  121
                ]
              }
            ]
          }
        },
        {
          name: "program"
        }
      ],
      args: [
        {
          name: "fee_tiers",
          type: {
            vec: {
              defined: {
                name: "FeeTier"
              }
            }
          }
        },
        {
          name: "offset",
          type: "u8"
        }
      ]
    }
  ],
  accounts: [
    {
      name: "BondingCurve",
      discriminator: [
        23,
        183,
        248,
        55,
        96,
        216,
        172,
        96
      ]
    },
    {
      name: "BuybackVault",
      discriminator: [
        153,
        166,
        71,
        144,
        179,
        189,
        137,
        251
      ]
    },
    {
      name: "DonationFeePda",
      discriminator: [
        246,
        197,
        96,
        9,
        193,
        30,
        93,
        115
      ]
    },
    {
      name: "FeeConfig",
      discriminator: [
        143,
        52,
        146,
        187,
        219,
        123,
        76,
        155
      ]
    },
    {
      name: "FeeProgramGlobal",
      discriminator: [
        162,
        165,
        245,
        49,
        29,
        37,
        55,
        242
      ]
    },
    {
      name: "Global",
      discriminator: [
        167,
        232,
        232,
        177,
        200,
        108,
        114,
        127
      ]
    },
    {
      name: "Pool",
      discriminator: [
        241,
        154,
        109,
        4,
        17,
        177,
        109,
        188
      ]
    },
    {
      name: "SharingConfig",
      discriminator: [
        216,
        74,
        9,
        0,
        56,
        140,
        93,
        75
      ]
    },
    {
      name: "SocialFeePda",
      discriminator: [
        139,
        96,
        53,
        17,
        42,
        169,
        206,
        150
      ]
    }
  ],
  events: [
    {
      name: "CreateFeeSharingConfigEvent",
      discriminator: [
        133,
        105,
        170,
        200,
        184,
        116,
        251,
        88
      ]
    },
    {
      name: "DonationFeePdaCranked",
      discriminator: [
        30,
        208,
        107,
        93,
        177,
        0,
        223,
        78
      ]
    },
    {
      name: "DonationFeePdaCreated",
      discriminator: [
        94,
        20,
        137,
        239,
        35,
        77,
        225,
        235
      ]
    },
    {
      name: "ExtendFeeConfigEvent",
      discriminator: [
        226,
        203,
        224,
        35,
        153,
        10,
        88,
        51
      ]
    },
    {
      name: "InitializeFeeConfigEvent",
      discriminator: [
        89,
        138,
        244,
        230,
        10,
        56,
        226,
        126
      ]
    },
    {
      name: "InitializeFeeProgramGlobalEvent",
      discriminator: [
        40,
        233,
        156,
        78,
        95,
        0,
        8,
        199
      ]
    },
    {
      name: "ResetFeeSharingConfigEvent",
      discriminator: [
        203,
        204,
        151,
        226,
        120,
        55,
        214,
        243
      ]
    },
    {
      name: "SetAuthorityEvent",
      discriminator: [
        18,
        175,
        132,
        66,
        208,
        201,
        87,
        242
      ]
    },
    {
      name: "SetClaimRateLimitEvent",
      discriminator: [
        13,
        143,
        143,
        235,
        181,
        19,
        51,
        40
      ]
    },
    {
      name: "SetDisableFlagsEvent",
      discriminator: [
        5,
        8,
        179,
        65,
        49,
        55,
        145,
        126
      ]
    },
    {
      name: "SetExoticFlatFeesEvent",
      discriminator: [
        195,
        138,
        108,
        15,
        8,
        77,
        68,
        9
      ]
    },
    {
      name: "SetSocialClaimAuthorityEvent",
      discriminator: [
        60,
        118,
        127,
        132,
        239,
        52,
        254,
        14
      ]
    },
    {
      name: "SocialFeePdaClaimed",
      discriminator: [
        50,
        18,
        193,
        65,
        237,
        210,
        234,
        236
      ]
    },
    {
      name: "SocialFeePdaCreated",
      discriminator: [
        183,
        183,
        218,
        147,
        24,
        124,
        137,
        169
      ]
    },
    {
      name: "SweepBuybackEvent",
      discriminator: [
        43,
        56,
        42,
        214,
        153,
        57,
        166,
        137
      ]
    },
    {
      name: "UpdateAdminEvent",
      discriminator: [
        225,
        152,
        171,
        87,
        246,
        63,
        66,
        234
      ]
    },
    {
      name: "UpdateFeeConfigEvent",
      discriminator: [
        90,
        23,
        65,
        35,
        62,
        244,
        188,
        208
      ]
    },
    {
      name: "UpdateFeeSharesEvent",
      discriminator: [
        21,
        186,
        196,
        184,
        91,
        228,
        225,
        203
      ]
    },
    {
      name: "UpdateStableFeeConfigEvent",
      discriminator: [
        94,
        5,
        43,
        237,
        103,
        147,
        232,
        245
      ]
    },
    {
      name: "UpsertFeeTiersEvent",
      discriminator: [
        171,
        89,
        169,
        187,
        122,
        186,
        33,
        204
      ]
    },
    {
      name: "UpsertStableFeeTiersEvent",
      discriminator: [
        232,
        237,
        237,
        52,
        98,
        146,
        73,
        243
      ]
    }
  ],
  errors: [
    {
      code: 6e3,
      name: "UnauthorizedProgram",
      msg: "Only Pump and PumpSwap programs can call this instruction"
    },
    {
      code: 6001,
      name: "InvalidAdmin",
      msg: "Invalid admin"
    },
    {
      code: 6002,
      name: "NoFeeTiers",
      msg: "No fee tiers provided"
    },
    {
      code: 6003,
      name: "TooManyFeeTiers",
      msg: "format"
    },
    {
      code: 6004,
      name: "OffsetNotContinuous",
      msg: "The offset should be <= fee_config.fee_tiers.len()"
    },
    {
      code: 6005,
      name: "FeeTiersNotSorted",
      msg: "Fee tiers must be sorted by market cap threshold (ascending)"
    },
    {
      code: 6006,
      name: "InvalidFeeTotal",
      msg: "Fee total must not exceed 10_000bps"
    },
    {
      code: 6007,
      name: "InvalidSharingConfig",
      msg: "Invalid Sharing Config"
    },
    {
      code: 6008,
      name: "InvalidPool",
      msg: "Invalid Pool"
    },
    {
      code: 6009,
      name: "SharingConfigAdminRevoked",
      msg: "Sharing config authority has been revoked - sharing config can only be updated once"
    },
    {
      code: 6010,
      name: "NoShareholders",
      msg: "No shareholders provided"
    },
    {
      code: 6011,
      name: "TooManyShareholders",
      msg: "format"
    },
    {
      code: 6012,
      name: "DuplicateShareholder",
      msg: "Duplicate shareholder address"
    },
    {
      code: 6013,
      name: "NotEnoughRemainingAccounts",
      msg: "Not enough remaining accounts"
    },
    {
      code: 6014,
      name: "InvalidShareTotal",
      msg: "Invalid share total - must equal 10_000 basis points"
    },
    {
      code: 6015,
      name: "ShareCalculationOverflow",
      msg: "Share calculation overflow"
    },
    {
      code: 6016,
      name: "NotAuthorized",
      msg: "The given account is not authorized to execute this instruction."
    },
    {
      code: 6017,
      name: "ZeroShareNotAllowed",
      msg: "Shareholder cannot have zero share"
    },
    {
      code: 6018,
      name: "SharingConfigNotActive",
      msg: "Fee sharing config is not active"
    },
    {
      code: 6019,
      name: "AmmAccountsRequiredForGraduatedCoin",
      msg: "AMM accounts are required for graduated coins"
    },
    {
      code: 6020,
      name: "ShareholderAccountMismatch",
      msg: "Remaining account key doesn't match shareholder address"
    },
    {
      code: 6021,
      name: "FeatureDeactivated",
      msg: "Feature is currently deactivated"
    },
    {
      code: 6022,
      name: "UserIdTooLong",
      msg: "User ID exceeds maximum length"
    },
    {
      code: 6023,
      name: "DeprecatedInstruction",
      msg: "Instruction is deprecated"
    },
    {
      code: 6024,
      name: "FeeSharesAlreadyUpdated",
      msg: "Reward split can only be updated once"
    },
    {
      code: 6025,
      name: "MathOverflow",
      msg: "Math overflow"
    },
    {
      code: 6026,
      name: "InvalidBuybackIndex",
      msg: "Invalid buybackindex"
    },
    {
      code: 6027,
      name: "ClaimRateLimitExceeded",
      msg: "Claim rate limit exceeded"
    },
    {
      code: 6028,
      name: "InvalidFeeConfigAccount",
      msg: "Account is not a valid FeeConfig for this instruction"
    },
    {
      code: 6029,
      name: "AccountTypeNotSupported",
      msg: "Account type not supported"
    },
    {
      code: 6030,
      name: "InvalidMint",
      msg: "Mint does not match quote mint"
    },
    {
      code: 6031,
      name: "UnsupportedQuoteMint",
      msg: "Unsupported quote mint"
    },
    {
      code: 6032,
      name: "InvalidRemainingAccounts",
      msg: "Invalid remaining accounts"
    }
  ],
  types: [
    {
      name: "BondingCurve",
      type: {
        kind: "struct",
        fields: [
          {
            name: "virtual_token_reserves",
            type: "u64"
          },
          {
            name: "virtual_quote_reserves",
            type: "u64"
          },
          {
            name: "real_token_reserves",
            type: "u64"
          },
          {
            name: "real_quote_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "complete",
            type: "bool"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          }
        ]
      }
    },
    {
      name: "BuybackVault",
      type: {
        kind: "struct",
        fields: [
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "total_claimed",
            type: "u64"
          },
          {
            name: "total_claimed_token1",
            type: "u64"
          },
          {
            name: "total_claimed_token2",
            type: "u64"
          },
          {
            name: "last_claimed",
            type: "i64"
          },
          {
            name: "claim_rate_limit",
            type: "i64"
          },
          {
            name: "_reserved",
            type: {
              array: [
                "u8",
                128
              ]
            }
          }
        ]
      }
    },
    {
      name: "ConfigStatus",
      type: {
        kind: "enum",
        variants: [
          {
            name: "Paused"
          },
          {
            name: "Active"
          }
        ]
      }
    },
    {
      name: "CreateFeeSharingConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "bonding_curve",
            type: "pubkey"
          },
          {
            name: "pool",
            type: {
              option: "pubkey"
            }
          },
          {
            name: "sharing_config",
            type: "pubkey"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "initial_shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          },
          {
            name: "status",
            type: {
              defined: {
                name: "ConfigStatus"
              }
            }
          }
        ]
      }
    },
    {
      name: "DonationFeePda",
      docs: [
        "Escrow PDA for donation relay: one per (mint, donation campaign `config_id`)."
      ],
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "version",
            type: "u8"
          },
          {
            name: "config_id",
            type: "pubkey"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "total_donated",
            type: "u64"
          },
          {
            name: "last_crank_ts",
            type: "i64"
          },
          {
            name: "_reserved",
            type: {
              array: [
                "u8",
                64
              ]
            }
          }
        ]
      }
    },
    {
      name: "DonationFeePdaCranked",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "signer",
            type: "pubkey"
          },
          {
            name: "donation_fee_pda",
            type: "pubkey"
          },
          {
            name: "config_id",
            type: "pubkey"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "amount",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "DonationFeePdaCreated",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "created_by",
            type: "pubkey"
          },
          {
            name: "donation_fee_pda",
            type: "pubkey"
          },
          {
            name: "config_id",
            type: "pubkey"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "creator",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "ExtendFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "fee_config",
            type: "pubkey"
          },
          {
            name: "user",
            type: "pubkey"
          },
          {
            name: "current_size",
            type: "u64"
          },
          {
            name: "new_size",
            type: "u64"
          },
          {
            name: "timestamp",
            type: "i64"
          }
        ]
      }
    },
    {
      name: "FeeConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            docs: [
              "The bump for the PDA"
            ],
            type: "u8"
          },
          {
            name: "admin",
            docs: [
              "The admin account that can update the fee config"
            ],
            type: "pubkey"
          },
          {
            name: "flat_fees",
            docs: [
              "The flat fees for non-pump pools"
            ],
            type: {
              defined: {
                name: "Fees"
              }
            }
          },
          {
            name: "fee_tiers",
            docs: [
              "The fee tiers"
            ],
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "stable_fee_tiers",
            docs: [
              "The fee tiers"
            ],
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "exotic_flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "FeeProgramGlobal",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "disable_flags",
            type: "u8"
          },
          {
            name: "social_claim_authority",
            type: "pubkey"
          },
          {
            name: "claim_rate_limit",
            type: "u64"
          },
          {
            name: "_reserved",
            type: {
              array: [
                "u8",
                256
              ]
            }
          }
        ]
      }
    },
    {
      name: "FeeTier",
      type: {
        kind: "struct",
        fields: [
          {
            name: "market_cap_lamports_threshold",
            type: "u128"
          },
          {
            name: "fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "Fees",
      type: {
        kind: "struct",
        fields: [
          {
            name: "lp_fee_bps",
            type: "u64"
          },
          {
            name: "protocol_fee_bps",
            type: "u64"
          },
          {
            name: "creator_fee_bps",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "Global",
      type: {
        kind: "struct",
        fields: [
          {
            name: "initialized",
            type: "bool"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "fee_recipient",
            type: "pubkey"
          },
          {
            name: "initial_virtual_token_reserves",
            type: "u64"
          },
          {
            name: "initial_virtual_sol_reserves",
            type: "u64"
          },
          {
            name: "initial_real_token_reserves",
            type: "u64"
          },
          {
            name: "token_total_supply",
            type: "u64"
          },
          {
            name: "fee_basis_points",
            type: "u64"
          },
          {
            name: "withdraw_authority",
            type: "pubkey"
          },
          {
            name: "enable_migrate",
            type: "bool"
          },
          {
            name: "pool_migration_fee",
            type: "u64"
          },
          {
            name: "creator_fee_basis_points",
            type: "u64"
          },
          {
            name: "fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          },
          {
            name: "set_creator_authority",
            type: "pubkey"
          },
          {
            name: "admin_set_creator_authority",
            type: "pubkey"
          },
          {
            name: "create_v2_enabled",
            type: "bool"
          },
          {
            name: "whitelist_pda",
            type: "pubkey"
          },
          {
            name: "reserved_fee_recipient",
            type: "pubkey"
          },
          {
            name: "mayhem_mode_enabled",
            type: "bool"
          },
          {
            name: "reserved_fee_recipients",
            type: {
              array: [
                "pubkey",
                7
              ]
            }
          }
        ]
      }
    },
    {
      name: "InitializeFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "fee_config",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "InitializeFeeProgramGlobalEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "authority",
            type: "pubkey"
          },
          {
            name: "social_claim_authority",
            type: "pubkey"
          },
          {
            name: "disable_flags",
            type: "u8"
          },
          {
            name: "claim_rate_limit",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "OptionBool",
      type: {
        kind: "struct",
        fields: [
          "bool"
        ]
      }
    },
    {
      name: "Pool",
      type: {
        kind: "struct",
        fields: [
          {
            name: "pool_bump",
            type: "u8"
          },
          {
            name: "index",
            type: "u16"
          },
          {
            name: "creator",
            type: "pubkey"
          },
          {
            name: "base_mint",
            type: "pubkey"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "lp_mint",
            type: "pubkey"
          },
          {
            name: "pool_base_token_account",
            type: "pubkey"
          },
          {
            name: "pool_quote_token_account",
            type: "pubkey"
          },
          {
            name: "lp_supply",
            type: "u64"
          },
          {
            name: "coin_creator",
            type: "pubkey"
          },
          {
            name: "is_mayhem_mode",
            type: "bool"
          },
          {
            name: "is_cashback_coin",
            type: "bool"
          },
          {
            name: "virtual_quote_reserves",
            type: "i128"
          }
        ]
      }
    },
    {
      name: "ResetFeeSharingConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "sharing_config",
            type: "pubkey"
          },
          {
            name: "old_admin",
            type: "pubkey"
          },
          {
            name: "old_shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          },
          {
            name: "new_admin",
            type: "pubkey"
          },
          {
            name: "new_shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          },
          {
            name: "old_version",
            type: "u8"
          },
          {
            name: "new_version",
            type: "u8"
          }
        ]
      }
    },
    {
      name: "SetAuthorityEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "old_authority",
            type: "pubkey"
          },
          {
            name: "new_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SetClaimRateLimitEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "claim_rate_limit",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "SetDisableFlagsEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "disable_flags",
            type: "u8"
          }
        ]
      }
    },
    {
      name: "SetExoticFlatFeesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "fee_config",
            type: "pubkey"
          },
          {
            name: "exotic_flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "SetSocialClaimAuthorityEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "social_claim_authority",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "Shareholder",
      type: {
        kind: "struct",
        fields: [
          {
            name: "address",
            type: "pubkey"
          },
          {
            name: "share_bps",
            type: "u16"
          }
        ]
      }
    },
    {
      name: "SharingConfig",
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "version",
            type: "u8"
          },
          {
            name: "status",
            type: {
              defined: {
                name: "ConfigStatus"
              }
            }
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "admin_revoked",
            type: "bool"
          },
          {
            name: "shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          }
        ]
      }
    },
    {
      name: "SocialFeePda",
      docs: [
        "Platform identifier: 0=pump, 1=twitter, etc."
      ],
      type: {
        kind: "struct",
        fields: [
          {
            name: "bump",
            type: "u8"
          },
          {
            name: "version",
            type: "u8"
          },
          {
            name: "user_id",
            docs: [
              "Max 20 characters to fit u64::MAX (18,446,744,073,709,551,615) as a string.",
              "Actual storage: 4 bytes (length prefix) + 20 bytes (content) = 24 bytes."
            ],
            type: "string"
          },
          {
            name: "platform",
            type: "u8"
          },
          {
            name: "total_claimed",
            type: "u64"
          },
          {
            name: "last_claimed",
            type: "u64"
          },
          {
            name: "total_stable_claimed",
            type: "u64"
          },
          {
            name: "_reserved",
            type: {
              array: [
                "u8",
                120
              ]
            }
          }
        ]
      }
    },
    {
      name: "SocialFeePdaClaimed",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "user_id",
            type: "string"
          },
          {
            name: "platform",
            type: "u8"
          },
          {
            name: "social_fee_pda",
            type: "pubkey"
          },
          {
            name: "recipient",
            type: "pubkey"
          },
          {
            name: "social_claim_authority",
            type: "pubkey"
          },
          {
            name: "amount_claimed",
            type: "u64"
          },
          {
            name: "claimable_before",
            type: "u64"
          },
          {
            name: "lifetime_claimed",
            type: "u64"
          },
          {
            name: "recipient_balance_before",
            type: "u64"
          },
          {
            name: "recipient_balance_after",
            type: "u64"
          },
          {
            name: "quote_mint",
            type: "pubkey"
          },
          {
            name: "lifetime_stable_claimed",
            type: "u64"
          }
        ]
      }
    },
    {
      name: "SocialFeePdaCreated",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "user_id",
            type: "string"
          },
          {
            name: "platform",
            type: "u8"
          },
          {
            name: "social_fee_pda",
            type: "pubkey"
          },
          {
            name: "created_by",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "SweepBuybackEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "index",
            type: "u8"
          },
          {
            name: "sol_amount",
            type: "u64"
          },
          {
            name: "token_amount",
            type: "u64"
          },
          {
            name: "destination",
            type: "pubkey"
          },
          {
            name: "buyback_vault",
            type: "pubkey"
          },
          {
            name: "mint",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "UpdateAdminEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "old_admin",
            type: "pubkey"
          },
          {
            name: "new_admin",
            type: "pubkey"
          }
        ]
      }
    },
    {
      name: "UpdateFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "fee_config",
            type: "pubkey"
          },
          {
            name: "fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "UpdateFeeSharesEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "mint",
            type: "pubkey"
          },
          {
            name: "sharing_config",
            type: "pubkey"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "new_shareholders",
            type: {
              vec: {
                defined: {
                  name: "Shareholder"
                }
              }
            }
          },
          {
            name: "version",
            type: "u8"
          }
        ]
      }
    },
    {
      name: "UpdateStableFeeConfigEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "fee_config",
            type: "pubkey"
          },
          {
            name: "stable_fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "flat_fees",
            type: {
              defined: {
                name: "Fees"
              }
            }
          }
        ]
      }
    },
    {
      name: "UpsertFeeTiersEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "fee_config",
            type: "pubkey"
          },
          {
            name: "fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "offset",
            type: "u8"
          }
        ]
      }
    },
    {
      name: "UpsertStableFeeTiersEvent",
      type: {
        kind: "struct",
        fields: [
          {
            name: "timestamp",
            type: "i64"
          },
          {
            name: "admin",
            type: "pubkey"
          },
          {
            name: "fee_config",
            type: "pubkey"
          },
          {
            name: "stable_fee_tiers",
            type: {
              vec: {
                defined: {
                  name: "FeeTier"
                }
              }
            }
          },
          {
            name: "offset",
            type: "u8"
          }
        ]
      }
    }
  ],
  constants: [
    {
      name: "AMM_CREATOR_VAULT_AUTHORITY_SEED",
      type: {
        array: [
          "u8",
          13
        ]
      },
      value: "[99, 114, 101, 97, 116, 111, 114, 95, 118, 97, 117, 108, 116]"
    },
    {
      name: "BUYBACK_VAULT_SEED",
      type: {
        array: [
          "u8",
          13
        ]
      },
      value: "[98, 117, 121, 98, 97, 99, 107, 45, 118, 97, 117, 108, 116]"
    },
    {
      name: "DEBOUNCER_V1",
      type: "bytes",
      value: "[100, 101, 98, 111, 117, 110, 99, 101, 114, 95, 118, 49]"
    },
    {
      name: "DONATION_FEE_PDA_SEED",
      type: {
        array: [
          "u8",
          16
        ]
      },
      value: "[100, 111, 110, 97, 116, 105, 111, 110, 45, 102, 101, 101, 45, 112, 100, 97]"
    },
    {
      name: "EPOCH_TRACKER_V1",
      type: "bytes",
      value: "[101, 112, 111, 99, 104, 95, 116, 114, 97, 99, 107, 101, 114, 95, 118, 49]"
    },
    {
      name: "FEE_CONFIG_SEED",
      type: "bytes",
      value: "[102, 101, 101, 95, 99, 111, 110, 102, 105, 103]"
    },
    {
      name: "FEE_PROGRAM_GLOBAL_SEED",
      type: {
        array: [
          "u8",
          18
        ]
      },
      value: "[102, 101, 101, 45, 112, 114, 111, 103, 114, 97, 109, 45, 103, 108, 111, 98, 97, 108]"
    },
    {
      name: "IX_DONATE_PUBKEY_CONFIG_ID_WITH_PAYER_V1",
      type: {
        array: [
          "u8",
          8
        ]
      },
      value: "[120, 217, 57, 241, 135, 104, 139, 184]"
    },
    {
      name: "MAX_BUYBACK_INDEX",
      type: "u8",
      value: "8"
    },
    {
      name: "MINT_WHITELIST_V1",
      type: "bytes",
      value: "[109, 105, 110, 116, 95, 119, 104, 105, 116, 101, 108, 105, 115, 116, 95, 118, 49]"
    },
    {
      name: "PUMP_CREATOR_VAULT_SEED",
      type: {
        array: [
          "u8",
          13
        ]
      },
      value: "[99, 114, 101, 97, 116, 111, 114, 45, 118, 97, 117, 108, 116]"
    },
    {
      name: "PUMP_GLOBAL_SEED",
      docs: [
        "Bonding Curve Program Global Seed"
      ],
      type: {
        array: [
          "u8",
          6
        ]
      },
      value: "[103, 108, 111, 98, 97, 108]"
    },
    {
      name: "SHARING_CONFIG_SEED",
      type: {
        array: [
          "u8",
          14
        ]
      },
      value: "[115, 104, 97, 114, 105, 110, 103, 45, 99, 111, 110, 102, 105, 103]"
    },
    {
      name: "SOCIAL_FEE_PDA_SEED",
      type: {
        array: [
          "u8",
          14
        ]
      },
      value: "[115, 111, 99, 105, 97, 108, 45, 102, 101, 101, 45, 112, 100, 97]"
    }
  ]
};

// src/onlineSdk.ts
var import_pump_swap_sdk = require("@pump-fun/pump-swap-sdk");
var import_spl_token2 = require("@solana/spl-token");
var import_web32 = require("@solana/web3.js");
var import_bn3 = __toESM(require("bn.js"));

// src/tokenIncentives.ts
var import_bn2 = __toESM(require("bn.js"));
function totalUnclaimedTokens(globalVolumeAccumulator, userVolumeAccumulator, currentTimestamp = Date.now() / 1e3) {
  const { startTime, endTime, secondsInADay, totalTokenSupply, solVolumes } = globalVolumeAccumulator;
  const { totalUnclaimedTokens: totalUnclaimedTokens2, currentSolVolume, lastUpdateTimestamp } = userVolumeAccumulator;
  const result = totalUnclaimedTokens2;
  if (startTime.eqn(0) || endTime.eqn(0) || secondsInADay.eqn(0)) {
    return result;
  }
  const currentTimestampBn = new import_bn2.default(currentTimestamp);
  if (currentTimestampBn.lt(startTime)) {
    return result;
  }
  const currentDayIndex = currentTimestampBn.sub(startTime).div(secondsInADay).toNumber();
  if (lastUpdateTimestamp.lt(startTime)) {
    return result;
  }
  const lastUpdatedIndex = lastUpdateTimestamp.sub(startTime).div(secondsInADay).toNumber();
  if (endTime.lt(startTime)) {
    return result;
  }
  const endDayIndex = endTime.sub(startTime).div(secondsInADay).toNumber();
  if (currentDayIndex > lastUpdatedIndex && lastUpdatedIndex <= endDayIndex) {
    const lastUpdatedDayTokenSupply = totalTokenSupply[lastUpdatedIndex];
    const lastUpdatedDaySolVolume = solVolumes[lastUpdatedIndex];
    if (lastUpdatedDaySolVolume.eqn(0)) {
      return result;
    }
    return result.add(
      currentSolVolume.mul(lastUpdatedDayTokenSupply).div(lastUpdatedDaySolVolume)
    );
  }
  return result;
}
function currentDayTokens(globalVolumeAccumulator, userVolumeAccumulator, currentTimestamp = Date.now() / 1e3) {
  const { startTime, endTime, secondsInADay, totalTokenSupply, solVolumes } = globalVolumeAccumulator;
  const { currentSolVolume, lastUpdateTimestamp } = userVolumeAccumulator;
  if (startTime.eqn(0) || endTime.eqn(0) || secondsInADay.eqn(0)) {
    return new import_bn2.default(0);
  }
  const currentTimestampBn = new import_bn2.default(currentTimestamp);
  if (currentTimestampBn.lt(startTime) || currentTimestampBn.gt(endTime)) {
    return new import_bn2.default(0);
  }
  const currentDayIndex = currentTimestampBn.sub(startTime).div(secondsInADay).toNumber();
  if (lastUpdateTimestamp.lt(startTime)) {
    return new import_bn2.default(0);
  }
  const lastUpdatedIndex = lastUpdateTimestamp.sub(startTime).div(secondsInADay).toNumber();
  if (endTime.lt(startTime)) {
    return new import_bn2.default(0);
  }
  if (currentDayIndex !== lastUpdatedIndex) {
    return new import_bn2.default(0);
  }
  const currentDayTokenSupply = totalTokenSupply[currentDayIndex];
  const currentDaySolVolume = solVolumes[currentDayIndex];
  if (currentDaySolVolume.eqn(0)) {
    return new import_bn2.default(0);
  }
  return currentSolVolume.mul(currentDayTokenSupply).div(currentDaySolVolume);
}

// src/onlineSdk.ts
var OFFLINE_PUMP_PROGRAM = getPumpProgram(null);
var GET_MULTIPLE_ACCOUNTS_MAX_KEYS = 100;
async function getMultipleAccountsInfoChunked(connection, keys) {
  const chunks = Array.from(
    { length: Math.ceil(keys.length / GET_MULTIPLE_ACCOUNTS_MAX_KEYS) },
    (_, index) => keys.slice(
      index * GET_MULTIPLE_ACCOUNTS_MAX_KEYS,
      (index + 1) * GET_MULTIPLE_ACCOUNTS_MAX_KEYS
    )
  );
  const results = await Promise.all(
    chunks.map((chunk) => connection.getMultipleAccountsInfo(chunk))
  );
  return results.flat();
}
function isQuoteTokenProgram(programId) {
  return programId.equals(import_spl_token2.TOKEN_PROGRAM_ID) || programId.equals(import_spl_token2.TOKEN_2022_PROGRAM_ID);
}
function quoteTokenProgramOf(mint, mintAccountInfo) {
  const { owner } = mintAccountInfo;
  if (!isQuoteTokenProgram(owner)) {
    throw new Error(
      `Quote mint ${mint.toBase58()} is owned by ${owner.toBase58()}, not by SPL Token or Token-2022`
    );
  }
  return owner;
}
function isTokenAccount(accountInfo, tokenProgram) {
  return accountInfo !== null && accountInfo.owner.equals(tokenProgram);
}
function supportedQuoteMints(globalAccountInfo, quoteControlAccountInfo) {
  if (!globalAccountInfo) {
    throw new Error(`Global account not found: ${GLOBAL_PDA.toBase58()}`);
  }
  const global = PUMP_SDK.decodeGlobal(globalAccountInfo);
  const quoteControl = quoteControlAccountInfo ? PUMP_SDK.decodeQuoteControl(quoteControlAccountInfo) : null;
  const supported = [
    {
      mint: import_spl_token2.NATIVE_MINT,
      source: "sol",
      initialVirtualQuoteReserves: global.initialVirtualSolReserves
    },
    ...global.whitelistedQuoteMints.filter((mint) => !isLegacyQuoteMint(mint)).map((mint) => ({
      mint,
      source: "global",
      initialVirtualQuoteReserves: global.initialVirtualQuoteReserves
    }))
  ];
  for (const entry of quoteControl?.mints ?? []) {
    if (!supported.some(({ mint }) => mint.equals(entry.mint))) {
      supported.push({
        mint: entry.mint,
        source: "quoteControl",
        initialVirtualQuoteReserves: entry.initialVirtualQuoteReserves
      });
    }
  }
  return supported;
}
function tokenAccountAmount(address, accountInfo, tokenProgram) {
  if (!isTokenAccount(accountInfo, tokenProgram)) {
    return new import_bn3.default(0);
  }
  const { amount } = (0, import_spl_token2.unpackAccount)(address, accountInfo, tokenProgram);
  return new import_bn3.default(amount.toString());
}
var OnlinePumpSdk = class {
  constructor(connection) {
    this.connection = connection;
    this.pumpProgram = getPumpProgram(connection);
    this.offlinePumpProgram = OFFLINE_PUMP_PROGRAM;
    this.pumpAmmProgram = getPumpAmmProgram(connection);
    this.pumpAmmSdk = new import_pump_swap_sdk.OnlinePumpAmmSdk(connection);
    this.pumpAmmAdminSdk = new import_pump_swap_sdk.PumpAmmAdminSdk(connection);
  }
  /**
   * The pump `Global` account, decoded by `PumpSdk.decodeGlobal` so the live
   * account still decodes while it is shorter than `GLOBAL_SIZE` (before
   * `extend_account` adds the newest fields).
   */
  async fetchGlobal() {
    const accountInfo = await this.connection.getAccountInfo(GLOBAL_PDA);
    if (!accountInfo) {
      throw new Error(`Global account not found: ${GLOBAL_PDA.toBase58()}`);
    }
    return PUMP_SDK.decodeGlobal(accountInfo);
  }
  async fetchFeeConfig() {
    const accountInfo = await this.connection.getAccountInfo(PUMP_FEE_CONFIG_PDA);
    if (!accountInfo) {
      throw new Error(
        `Fee config account not found: ${PUMP_FEE_CONFIG_PDA.toBase58()}`
      );
    }
    return PUMP_SDK.decodeFeeConfig(accountInfo);
  }
  /**
   * The pump `QuoteControl` PDA, or `null` while it is uninitialized (the
   * program treats a missing account as an empty mint list). Only a missing
   * account yields `null`: an account at the PDA that does not decode as a
   * `QuoteControl` throws (Anchor `fetchNullable`), unlike
   * `PumpSdk.decodeQuoteControlNullable`, which maps decode failures to
   * `null`.
   */
  async fetchQuoteControl() {
    return await this.pumpProgram.account.quoteControl.fetchNullable(
      QUOTE_CONTROL_PDA
    );
  }
  /**
   * The program that owns `quoteMint`, which every quote-side ATA and every
   * `quoteTokenProgram` parameter in this SDK must use. WSOL and the zero key
   * resolve to `TOKEN_PROGRAM_ID` without an RPC call; any other mint is
   * fetched and must be owned by SPL Token or Token-2022 (a missing account or
   * another owner throws). That includes the Token-2022 native mint, which
   * resolves to its owner, `TOKEN_2022_PROGRAM_ID`: it is SOL-like for fee
   * selection only, and `create_v2` rejects it as a quote.
   */
  async fetchQuoteTokenProgram(quoteMint) {
    if (isLegacyQuoteMint(quoteMint)) {
      return import_spl_token2.TOKEN_PROGRAM_ID;
    }
    const mintAccountInfo = await this.connection.getAccountInfo(quoteMint);
    if (!mintAccountInfo) {
      throw new Error(`Quote mint account not found: ${quoteMint.toBase58()}`);
    }
    return quoteTokenProgramOf(quoteMint, mintAccountInfo);
  }
  /**
   * Every quote mint `create_v2` accepts right now, in one RPC round-trip: SOL
   * (as `NATIVE_MINT`, seeded from `Global.initialVirtualSolReserves`), the
   * non-zero `Global.whitelistedQuoteMints` slots, then the `QuoteControl`
   * entries `Global` does not already list. The PDA is the only source of
   * quote-control mints; while it is uninitialized the list is SOL plus the
   * `Global` whitelist.
   */
  async fetchSupportedQuoteMints() {
    const [globalAccountInfo, quoteControlAccountInfo] = await this.connection.getMultipleAccountsInfo([
      GLOBAL_PDA,
      QUOTE_CONTROL_PDA
    ]);
    return supportedQuoteMints(globalAccountInfo, quoteControlAccountInfo);
  }
  /**
   * `fetchSupportedQuoteMints` narrowed to one mint, plus what a builder needs
   * for it: the owning token program and the mint's decimals. SOL-like inputs
   * (`NATIVE_MINT`, the zero key, `undefined`) resolve to the `sol` entry. One
   * RPC round-trip.
   *
   * @throws {UnsupportedQuoteMintError} when the mint is in neither list,
   *   `create_v2`'s first admission check. A listed mint can still be rejected
   *   on chain: a `quoteTokenProgram` that is not its owner or a Token-2022
   *   extension outside the xStock set (6063), or `mayhemMode` with a mint
   *   admitted only through `QuoteControl` (6071).
   */
  async resolveQuoteMint(quoteMint = import_spl_token2.NATIVE_MINT) {
    const mint = normalizeQuoteMint(quoteMint);
    const [globalAccountInfo, quoteControlAccountInfo, mintAccountInfo] = await this.connection.getMultipleAccountsInfo([
      GLOBAL_PDA,
      QUOTE_CONTROL_PDA,
      mint
    ]);
    const supported = supportedQuoteMints(
      globalAccountInfo,
      quoteControlAccountInfo
    ).find((entry) => entry.mint.equals(mint));
    if (!supported) {
      throw new UnsupportedQuoteMintError(mint);
    }
    if (!mintAccountInfo) {
      throw new Error(`Quote mint account not found: ${mint.toBase58()}`);
    }
    const quoteTokenProgram = quoteTokenProgramOf(mint, mintAccountInfo);
    const { decimals } = (0, import_spl_token2.unpackMint)(mint, mintAccountInfo, quoteTokenProgram);
    return { ...supported, quoteTokenProgram, decimals };
  }
  /**
   * @deprecated use PumpSdk.decodeBondingCurveNullable instead.
   */
  async fetchBondingCurve(mint) {
    const bondingCurve = bondingCurvePda(mint);
    const accountInfo = await this.connection.getAccountInfo(bondingCurve);
    if (!accountInfo) {
      throw new Error(
        `Bonding curve account not found: ${bondingCurve.toBase58()}`
      );
    }
    return PUMP_SDK.decodeBondingCurve(accountInfo);
  }
  /**
   * The state `buyV2Instructions` needs, plus the curve's normalized
   * `quoteMint` (`NATIVE_MINT` for SOL curves) and `quoteTokenProgram` (the
   * mint's owner) to forward to it.
   *
   * @param quoteMint - Optional hint: the curve's quote mint when the caller
   *   already knows it (from an earlier fetch, `resolveQuoteMint`, or an
   *   indexer). A curve stores its quote mint, so for a non-SOL curve the
   *   token program is only known after decoding the curve: without the hint
   *   that is a second RPC round-trip; with a correct hint the mint account
   *   joins the first batch. A hint that does not match the curve is ignored
   *   (the second round-trip happens). SOL curves never need one.
   */
  async fetchBuyState(mint, user, tokenProgram = import_spl_token2.TOKEN_PROGRAM_ID, quoteMint) {
    const quoteMintHint = this.quoteMintHint(quoteMint);
    const [
      bondingCurveAccountInfo,
      associatedUserAccountInfo,
      quoteMintHintAccountInfo
    ] = await this.connection.getMultipleAccountsInfo([
      bondingCurvePda(mint),
      (0, import_spl_token2.getAssociatedTokenAddressSync)(mint, user, true, tokenProgram),
      ...quoteMintHint ? [quoteMintHint] : []
    ]);
    if (!bondingCurveAccountInfo) {
      throw new Error(
        `Bonding curve account not found for mint: ${mint.toBase58()}`
      );
    }
    const bondingCurve = PUMP_SDK.decodeBondingCurve(bondingCurveAccountInfo);
    const quote = await this.curveQuote(
      bondingCurve,
      quoteMintHint,
      quoteMintHintAccountInfo
    );
    return {
      bondingCurveAccountInfo,
      bondingCurve,
      associatedUserAccountInfo,
      ...quote
    };
  }
  /**
   * The state `sellV2Instructions` needs, plus the curve's normalized
   * `quoteMint` and `quoteTokenProgram`. `quoteMint` is the same optional
   * hint as on `fetchBuyState`.
   */
  async fetchSellState(mint, user, tokenProgram = import_spl_token2.TOKEN_PROGRAM_ID, quoteMint) {
    const quoteMintHint = this.quoteMintHint(quoteMint);
    const [
      bondingCurveAccountInfo,
      associatedUserAccountInfo,
      quoteMintHintAccountInfo
    ] = await this.connection.getMultipleAccountsInfo([
      bondingCurvePda(mint),
      (0, import_spl_token2.getAssociatedTokenAddressSync)(mint, user, true, tokenProgram),
      ...quoteMintHint ? [quoteMintHint] : []
    ]);
    if (!bondingCurveAccountInfo) {
      throw new Error(
        `Bonding curve account not found for mint: ${mint.toBase58()}`
      );
    }
    if (!associatedUserAccountInfo) {
      throw new Error(
        `Associated token account not found for mint: ${mint.toBase58()} and user: ${user.toBase58()}`
      );
    }
    const bondingCurve = PUMP_SDK.decodeBondingCurve(bondingCurveAccountInfo);
    const quote = await this.curveQuote(
      bondingCurve,
      quoteMintHint,
      quoteMintHintAccountInfo
    );
    return { bondingCurveAccountInfo, bondingCurve, ...quote };
  }
  // A quote mint worth fetching alongside the curve: SOL needs no lookup.
  quoteMintHint(quoteMint) {
    return quoteMint && !isLegacyQuoteMint(quoteMint) ? quoteMint : null;
  }
  /**
   * The quote mint a decoded curve trades in (normalized) and the program
   * that owns it. SOL curves need no RPC; another curve uses the hinted mint
   * account when the hint is the curve's own quote, else one more fetch.
   */
  async curveQuote(bondingCurve, quoteMintHint, quoteMintHintAccountInfo) {
    const quoteMint = normalizeQuoteMint(bondingCurve.quoteMint);
    if (quoteMint.equals(import_spl_token2.NATIVE_MINT)) {
      return { quoteMint, quoteTokenProgram: import_spl_token2.TOKEN_PROGRAM_ID };
    }
    if (quoteMintHint?.equals(quoteMint) && quoteMintHintAccountInfo) {
      return {
        quoteMint,
        quoteTokenProgram: quoteTokenProgramOf(
          quoteMint,
          quoteMintHintAccountInfo
        )
      };
    }
    return {
      quoteMint,
      quoteTokenProgram: await this.fetchQuoteTokenProgram(quoteMint)
    };
  }
  async fetchGlobalVolumeAccumulator() {
    return await this.pumpProgram.account.globalVolumeAccumulator.fetch(
      GLOBAL_VOLUME_ACCUMULATOR_PDA
    );
  }
  async fetchUserVolumeAccumulator(user) {
    return await this.pumpProgram.account.userVolumeAccumulator.fetchNullable(
      userVolumeAccumulatorPda(user)
    );
  }
  async fetchUserVolumeAccumulatorTotalStats(user) {
    const userVolumeAccumulator = await this.fetchUserVolumeAccumulator(
      user
    ) ?? {
      totalUnclaimedTokens: new import_bn3.default(0),
      totalClaimedTokens: new import_bn3.default(0),
      currentSolVolume: new import_bn3.default(0)
    };
    const userVolumeAccumulatorAmm = await this.pumpAmmSdk.fetchUserVolumeAccumulator(user) ?? {
      totalUnclaimedTokens: new import_bn3.default(0),
      totalClaimedTokens: new import_bn3.default(0),
      currentSolVolume: new import_bn3.default(0)
    };
    return {
      totalUnclaimedTokens: userVolumeAccumulator.totalUnclaimedTokens.add(
        userVolumeAccumulatorAmm.totalUnclaimedTokens
      ),
      totalClaimedTokens: userVolumeAccumulator.totalClaimedTokens.add(
        userVolumeAccumulatorAmm.totalClaimedTokens
      ),
      currentSolVolume: userVolumeAccumulator.currentSolVolume.add(
        userVolumeAccumulatorAmm.currentSolVolume
      )
    };
  }
  async collectCoinCreatorFeeInstructions(coinCreator, feePayer) {
    const quoteMint = import_spl_token2.NATIVE_MINT;
    const quoteTokenProgram = import_spl_token2.TOKEN_PROGRAM_ID;
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk.coinCreatorVaultAuthorityPda)(coinCreator);
    const coinCreatorVaultAta = (0, import_pump_swap_sdk.coinCreatorVaultAtaPda)(
      coinCreatorVaultAuthority,
      quoteMint,
      quoteTokenProgram
    );
    const coinCreatorTokenAccount = (0, import_spl_token2.getAssociatedTokenAddressSync)(
      quoteMint,
      coinCreator,
      true,
      quoteTokenProgram
    );
    const [coinCreatorVaultAtaAccountInfo, coinCreatorTokenAccountInfo] = await this.connection.getMultipleAccountsInfo([
      coinCreatorVaultAta,
      coinCreatorTokenAccount
    ]);
    return [
      await this.offlinePumpProgram.methods.collectCreatorFee().accountsPartial({
        creator: coinCreator
      }).instruction(),
      ...await import_pump_swap_sdk.PUMP_AMM_SDK.collectCoinCreatorFee(
        {
          coinCreator,
          quoteMint,
          quoteTokenProgram,
          coinCreatorVaultAuthority,
          coinCreatorVaultAta,
          coinCreatorTokenAccount,
          coinCreatorVaultAtaAccountInfo,
          coinCreatorTokenAccountInfo
        },
        feePayer
      )
    ];
  }
  /**
   * Collects a creator's fees in one quote from the pump creator vault and
   * the pump-amm coin creator vault. `quoteTokenProgram` must be the program
   * that owns `quoteMint` (`fetchQuoteTokenProgram`). Assumes the creator's
   * quote ATA exists for a non-SOL quote: neither program creates it (see
   * `collectCoinCreatorFeeAllQuotesInstructions`, which does).
   */
  async collectCoinCreatorFeeV2Instructions(coinCreator, quoteMint, quoteTokenProgram, feePayer) {
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk.coinCreatorVaultAuthorityPda)(coinCreator);
    const coinCreatorVaultAta = (0, import_pump_swap_sdk.coinCreatorVaultAtaPda)(
      coinCreatorVaultAuthority,
      quoteMint,
      quoteTokenProgram
    );
    const coinCreatorTokenAccount = (0, import_spl_token2.getAssociatedTokenAddressSync)(
      quoteMint,
      coinCreator,
      true,
      quoteTokenProgram
    );
    const [coinCreatorVaultAtaAccountInfo, coinCreatorTokenAccountInfo] = await this.connection.getMultipleAccountsInfo([
      coinCreatorVaultAta,
      coinCreatorTokenAccount
    ]);
    const pumpAmmInstructions = coinCreatorVaultAtaAccountInfo ? await import_pump_swap_sdk.PUMP_AMM_SDK.collectCoinCreatorFee(
      {
        coinCreator,
        quoteMint,
        quoteTokenProgram,
        coinCreatorVaultAuthority,
        coinCreatorVaultAta,
        coinCreatorTokenAccount,
        coinCreatorVaultAtaAccountInfo,
        coinCreatorTokenAccountInfo
      },
      feePayer
    ) : [];
    return [
      await this.offlinePumpProgram.methods.collectCreatorFeeV2().accountsPartial({
        creator: coinCreator,
        quoteMint,
        quoteTokenProgram,
        creatorVault: creatorVaultPda(coinCreator)
      }).instruction(),
      ...pumpAmmInstructions
    ];
  }
  /**
   * Collects a creator's fees in every quote mint currently listed on `Global`
   * or in the `QuoteControl` PDA (`fetchSupportedQuoteMints`), plus
   * `extraQuoteMints`, from both the pump creator vault and the pump-amm coin
   * creator vault, into the creator's wallet and quote ATAs. For SOL: the
   * lamport vault (`collect_creator_fee`) and, when the AMM WSOL vault ATA
   * exists, the AMM leg (which wraps and unwraps by itself). For every other
   * quote, in this order: an idempotent create of the creator's quote ATA when
   * it is missing (neither program creates it), the pump
   * `collect_creator_fee_v2` leg only when the pump vault's quote ATA exists,
   * and the AMM leg only when its vault ATA exists; a quote with neither vault
   * ATA contributes nothing. "Exists" means a token account of the quote's
   * program: any other account at a vault ATA address is treated as absent
   * (the programs could not deserialize it), and one at the creator's ATA
   * address is created over. Three RPC round-trips: the supported mints, their
   * owners, then every vault and destination ATA (in batches of 100 keys).
   *
   * De-listing a mint from `QuoteControl` stops new creates only: curves
   * already quoted in it keep trading and accruing fees, and this method does
   * not know about them. Pass such mints (from an indexer, or the creator's
   * own coins' `bondingCurve.quoteMint`) as `extraQuoteMints`. A listed or
   * extra mint whose account is missing or is not a token mint is skipped
   * (no ATA can exist for it, so nothing is lost).
   *
   * Each quote's instructions are contiguous, so the result can be split per
   * quote when it does not fit one transaction (up to four instructions for
   * SOL, three per token quote).
   *
   * @param feePayer - Signs and pays ATA rent; defaults to the creator.
   * @param extraQuoteMints - Quote mints to sweep in addition to the listed
   *   ones, e.g. de-listed mints the creator's coins are quoted in. SOL-like
   *   keys and duplicates are ignored.
   */
  async collectCoinCreatorFeeAllQuotesInstructions(coinCreator, feePayer, extraQuoteMints = []) {
    const payer = feePayer ?? coinCreator;
    const supported = await this.fetchSupportedQuoteMints();
    const mints = extraQuoteMints.map((mint) => normalizeQuoteMint(mint)).reduce(
      (all, mint) => all.some((known) => known.equals(mint)) ? all : [...all, mint],
      supported.map(({ mint }) => mint)
    );
    const quotes = await this.fetchQuoteMintPrograms(mints);
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk.coinCreatorVaultAuthorityPda)(coinCreator);
    const creatorVault = creatorVaultPda(coinCreator);
    const vaultAccounts = quotes.map(({ mint, quoteTokenProgram }) => ({
      pumpVaultAta: quoteAta(creatorVault, mint, quoteTokenProgram),
      ammVaultAta: (0, import_pump_swap_sdk.coinCreatorVaultAtaPda)(
        coinCreatorVaultAuthority,
        mint,
        quoteTokenProgram
      ),
      creatorAta: (0, import_spl_token2.getAssociatedTokenAddressSync)(
        mint,
        coinCreator,
        true,
        quoteTokenProgram
      )
    }));
    const accountInfos = await getMultipleAccountsInfoChunked(
      this.connection,
      vaultAccounts.flatMap(({ pumpVaultAta, ammVaultAta, creatorAta }) => [
        pumpVaultAta,
        ammVaultAta,
        creatorAta
      ])
    );
    const instructions = [];
    for (const [index, { mint, quoteTokenProgram }] of quotes.entries()) {
      const { ammVaultAta, creatorAta } = vaultAccounts[index];
      const [
        pumpVaultAtaAccountInfo,
        ammVaultAtaAccountInfo,
        creatorAtaAccountInfo
      ] = accountInfos.slice(index * 3, index * 3 + 3);
      const isSol = mint.equals(import_spl_token2.NATIVE_MINT);
      const collectPump = isSol || isTokenAccount(pumpVaultAtaAccountInfo, quoteTokenProgram);
      const collectAmm = isTokenAccount(
        ammVaultAtaAccountInfo,
        quoteTokenProgram
      );
      if (!collectPump && !collectAmm) {
        continue;
      }
      if (!isSol && !isTokenAccount(creatorAtaAccountInfo, quoteTokenProgram)) {
        instructions.push(
          (0, import_spl_token2.createAssociatedTokenAccountIdempotentInstruction)(
            payer,
            creatorAta,
            coinCreator,
            mint,
            quoteTokenProgram
          )
        );
      }
      if (collectPump) {
        instructions.push(
          isSol ? await this.offlinePumpProgram.methods.collectCreatorFee().accountsPartial({ creator: coinCreator }).instruction() : await this.offlinePumpProgram.methods.collectCreatorFeeV2().accountsPartial({
            creator: coinCreator,
            quoteMint: mint,
            quoteTokenProgram,
            creatorVault
          }).instruction()
        );
      }
      if (collectAmm) {
        instructions.push(
          ...await import_pump_swap_sdk.PUMP_AMM_SDK.collectCoinCreatorFee(
            {
              coinCreator,
              quoteMint: mint,
              quoteTokenProgram,
              coinCreatorVaultAuthority,
              coinCreatorVaultAta: ammVaultAta,
              coinCreatorTokenAccount: creatorAta,
              coinCreatorVaultAtaAccountInfo: ammVaultAtaAccountInfo,
              coinCreatorTokenAccountInfo: creatorAtaAccountInfo
            },
            feePayer
          )
        );
      }
    }
    return instructions;
  }
  /**
   * What a creator has waiting in each quote mint currently listed on `Global`
   * or in the `QuoteControl` PDA (`fetchSupportedQuoteMints`): the pump
   * creator vault (lamports above rent for SOL, the vault ATA's token amount
   * otherwise) and the pump-amm coin creator vault ATA. An account at a vault
   * ATA address that is not a token account of the quote's program counts as
   * zero. Up to four RPC round-trips (the vault batch in slices of 100 keys).
   *
   * Like `collectCoinCreatorFeeAllQuotesInstructions`, this does not see fees
   * in a mint that has since been de-listed: read those vault ATAs
   * (`quoteAta(creatorVaultPda(creator), mint, program)` and the pump-amm
   * `coinCreatorVaultAtaPda`) directly. A listed mint whose account is missing
   * or is not a token mint is left out.
   */
  async getCreatorVaultQuoteBalances(creator) {
    const quotes = await this.fetchSupportedQuoteMintPrograms();
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk.coinCreatorVaultAuthorityPda)(creator);
    const creatorVault = creatorVaultPda(creator);
    const vaultAccounts = quotes.map(({ mint, quoteTokenProgram }) => ({
      pumpVaultAta: quoteAta(creatorVault, mint, quoteTokenProgram),
      ammVaultAta: (0, import_pump_swap_sdk.coinCreatorVaultAtaPda)(
        coinCreatorVaultAuthority,
        mint,
        quoteTokenProgram
      )
    }));
    const [creatorVaultAccountInfo, ...accountInfos] = await getMultipleAccountsInfoChunked(this.connection, [
      creatorVault,
      ...vaultAccounts.flatMap(({ pumpVaultAta, ammVaultAta }) => [
        pumpVaultAta,
        ammVaultAta
      ])
    ]);
    const solVaultBalance = await this.creatorVaultLamportsAboveRent(
      creatorVaultAccountInfo
    );
    return quotes.map(({ mint, source, quoteTokenProgram }, index) => {
      const { pumpVaultAta, ammVaultAta } = vaultAccounts[index];
      const [pumpVaultAtaAccountInfo, ammVaultAtaAccountInfo] = accountInfos.slice(index * 2, index * 2 + 2);
      const pumpVault = mint.equals(import_spl_token2.NATIVE_MINT) ? solVaultBalance : tokenAccountAmount(
        pumpVaultAta,
        pumpVaultAtaAccountInfo,
        quoteTokenProgram
      );
      const ammVault = tokenAccountAmount(
        ammVaultAta,
        ammVaultAtaAccountInfo,
        quoteTokenProgram
      );
      return {
        mint,
        source,
        quoteTokenProgram,
        pumpVault,
        ammVault,
        total: pumpVault.add(ammVault)
      };
    });
  }
  // Every supported quote mint with the program that owns it, dropping the
  // entries `fetchQuoteMintPrograms` cannot resolve.
  async fetchSupportedQuoteMintPrograms() {
    const supported = await this.fetchSupportedQuoteMints();
    const quotes = await this.fetchQuoteMintPrograms(
      supported.map(({ mint }) => mint)
    );
    return quotes.map(({ mint, quoteTokenProgram }) => ({
      // Present by construction: `fetchQuoteMintPrograms` only drops entries.
      ...supported.find((entry) => entry.mint.equals(mint)),
      quoteTokenProgram
    }));
  }
  // `mints` (normalized; SOL as `NATIVE_MINT`) with the program that owns each,
  // in order: SOL without a lookup, the others from one chunked fetch of their
  // mint accounts. A mint whose account is missing or is owned by neither token
  // program is dropped rather than thrown on: `add_quote_control_mint` does not
  // check the mint exists, and no ATA can exist for such a mint, so a sweep or
  // balance over the remaining mints is complete.
  async fetchQuoteMintPrograms(mints) {
    const tokenMints = mints.filter((mint) => !mint.equals(import_spl_token2.NATIVE_MINT));
    const mintAccountInfos = await getMultipleAccountsInfoChunked(
      this.connection,
      tokenMints
    );
    const programs = new Map(
      tokenMints.flatMap((mint, index) => {
        const owner = mintAccountInfos[index]?.owner;
        return owner && isQuoteTokenProgram(owner) ? [[mint.toBase58(), owner]] : [];
      })
    );
    return mints.flatMap((mint) => {
      if (mint.equals(import_spl_token2.NATIVE_MINT)) {
        return [{ mint, quoteTokenProgram: import_spl_token2.TOKEN_PROGRAM_ID }];
      }
      const quoteTokenProgram = programs.get(mint.toBase58());
      return quoteTokenProgram ? [{ mint, quoteTokenProgram }] : [];
    });
  }
  // `getCreatorVaultBalance` over an already fetched vault account.
  async creatorVaultLamportsAboveRent(accountInfo) {
    if (accountInfo === null) {
      return new import_bn3.default(0);
    }
    const rentExemptionLamports = await this.connection.getMinimumBalanceForRentExemption(
      accountInfo.data.length
    );
    if (accountInfo.lamports < rentExemptionLamports) {
      return new import_bn3.default(0);
    }
    return new import_bn3.default(accountInfo.lamports - rentExemptionLamports);
  }
  /**
   * `PumpSdk.adminCtoInstruction` for `mint`, with the signer defaulting to
   * `Global.adminSetCreatorAuthority` and every other account resolved from
   * chain: `Global` and the curve in one round-trip, plus the quote mint's
   * owner program for a token quote. Returned as
   * `[setComputeUnitLimit(ADMIN_CTO_COMPUTE_UNIT_LIMIT), admin_cto]`.
   *
   * Rejects up front, with typed errors, what the program would reject
   * (`admin_cto.rs`): a mayhem coin (`CtoNotAllowedForMayhemCoinError`, 6088),
   * changing a holder-reward coin's creator (`HolderRewardCreatorImmutableError`,
   * 6083; only `isHolderReward: true` again is allowed), converting while
   * `Global.isHolderRewardEnabled` is off (`HolderRewardDisabledError`, 6084),
   * a missing `newCreator` on the new-creator path or a present one on the
   * holder path (6089 / 6090), and for a `creatorFeeBps`: a SOL or
   * `Global`-whitelisted quote (`CreatorFeeNotConfigurableForQuoteError`,
   * 6091), a coin that stays cashback
   * (`CreatorFeeNotAllowedForCashbackCoinError`, 6080), the gate off
   * (`CreatorFeeNotConfigurableError`, 6077) and a rate outside
   * `1..=Global.maxConfigurableCreatorFeeBps` (`CreatorFeeBpsOutOfRangeError`,
   * 6078). The program alone judges the rest (a `newCreator` equal to a PDA,
   * a frozen shared vault, ...).
   */
  async adminCtoInstructions(mint, {
    isHolderReward,
    creatorFeeBps,
    newCreator,
    adminSetCreatorAuthority
  }) {
    const { global, bondingCurve, quoteMint, quoteTokenProgram } = await this.fetchCurveWithQuote(mint);
    if (bondingCurve.isMayhemMode) {
      throw new CtoNotAllowedForMayhemCoinError(mint);
    }
    const toHolder = isHolderReward === true;
    if (bondingCurve.isHolderReward && !toHolder) {
      throw new HolderRewardCreatorImmutableError(mint);
    }
    if (toHolder) {
      if (!bondingCurve.isHolderReward && !global.isHolderRewardEnabled) {
        throw new HolderRewardDisabledError();
      }
      if (newCreator) {
        throw new Error(
          "newCreator must be omitted when converting to holder rewards"
        );
      }
    } else if (!newCreator) {
      throw new Error(
        "newCreator is required unless converting to holder rewards"
      );
    }
    if (creatorFeeBps) {
      const quoteIsSolOrWhitelisted = isLegacyQuoteMint(bondingCurve.quoteMint) || global.whitelistedQuoteMints.some(
        (whitelisted) => whitelisted.equals(bondingCurve.quoteMint)
      );
      if (quoteIsSolOrWhitelisted) {
        throw new CreatorFeeNotConfigurableForQuoteError(quoteMint);
      }
      if (bondingCurve.isCashbackCoin && !toHolder) {
        throw new CreatorFeeNotAllowedForCashbackCoinError(mint);
      }
      if (!global.creatorFeeConfigurable) {
        throw new CreatorFeeNotConfigurableError();
      }
      if (creatorFeeBps.ltn(1) || creatorFeeBps.gt(global.maxConfigurableCreatorFeeBps)) {
        throw new CreatorFeeBpsOutOfRangeError(
          creatorFeeBps,
          global.maxConfigurableCreatorFeeBps
        );
      }
    }
    return [
      import_web32.ComputeBudgetProgram.setComputeUnitLimit({
        units: ADMIN_CTO_COMPUTE_UNIT_LIMIT
      }),
      await PUMP_SDK.adminCtoInstruction({
        adminSetCreatorAuthority: adminSetCreatorAuthority ?? global.adminSetCreatorAuthority,
        mint,
        currentCreator: bondingCurve.creator,
        quoteMint,
        quoteTokenProgram,
        isHolderReward,
        creatorFeeBps,
        newCreator
      })
    ];
  }
  /**
   * `PumpSdk.updateHolderRewardConfigInstruction` with `authority` defaulting
   * to the current `Global.authority`, the only key the program accepts.
   */
  async adminUpdateHolderRewardConfigInstruction({
    isHolderRewardEnabled,
    holderRewardClaimAuthority,
    authority
  }) {
    return await PUMP_SDK.updateHolderRewardConfigInstruction({
      authority: authority ?? (await this.fetchGlobal()).authority,
      isHolderRewardEnabled,
      holderRewardClaimAuthority
    });
  }
  /**
   * `PumpSdk.distributeFeeToHoldersInstruction` for `mint`, with the signer
   * defaulting to `Global.holderRewardClaimAuthority`, the quote read from
   * the curve, and the PDA's quote ATA passed as `holderRewardsTokenAccount`
   * when it exists (on a SOL quote it is a parked WSOL account the program
   * sweeps first; on a token quote it is the payout source and this throws
   * when it is missing, since there is nothing to pay from). Throws when the
   * coin is not a holder-reward coin.
   */
  async distributeFeeToHoldersInstructions(mint, recipients, holderRewardClaimAuthority) {
    const { global, bondingCurve, quoteMint, quoteTokenProgram } = await this.fetchCurveWithQuote(mint);
    if (!bondingCurve.isHolderReward) {
      throw new Error(
        `Mint ${mint.toBase58()} is not a holder-reward coin; nothing to distribute`
      );
    }
    const holderRewardsAta = quoteAta(
      holderRewardsPda(mint),
      quoteMint,
      quoteTokenProgram
    );
    const holderRewardsAtaAccountInfo = await this.connection.getAccountInfo(holderRewardsAta);
    if (!holderRewardsAtaAccountInfo && !quoteMint.equals(import_spl_token2.NATIVE_MINT)) {
      throw new Error(
        `Holder-rewards token account ${holderRewardsAta.toBase58()} does not exist; collect the coin's creator fees onto the PDA first`
      );
    }
    return [
      await PUMP_SDK.distributeFeeToHoldersInstruction({
        holderRewardClaimAuthority: holderRewardClaimAuthority ?? global.holderRewardClaimAuthority,
        mint,
        quoteMint,
        quoteTokenProgram,
        recipients,
        holderRewardsTokenAccount: holderRewardsAtaAccountInfo ? holderRewardsAta : void 0
      })
    ];
  }
  /**
   * `Global` and `mint`'s curve in one round-trip, with the curve's quote
   * normalized (`NATIVE_MINT` for SOL curves) and the program that owns it
   * (a second round-trip for a token quote, none for SOL).
   */
  async fetchCurveWithQuote(mint) {
    const [globalAccountInfo, bondingCurveAccountInfo] = await this.connection.getMultipleAccountsInfo([
      GLOBAL_PDA,
      bondingCurvePda(mint)
    ]);
    if (!globalAccountInfo) {
      throw new Error(`Global account not found: ${GLOBAL_PDA.toBase58()}`);
    }
    if (!bondingCurveAccountInfo) {
      throw new Error(
        `Bonding curve account not found for mint: ${mint.toBase58()}`
      );
    }
    const global = PUMP_SDK.decodeGlobal(globalAccountInfo);
    const bondingCurve = PUMP_SDK.decodeBondingCurve(bondingCurveAccountInfo);
    const quoteMint = normalizeQuoteMint(bondingCurve.quoteMint);
    return {
      global,
      bondingCurve,
      quoteMint,
      quoteTokenProgram: await this.fetchQuoteTokenProgram(quoteMint)
    };
  }
  /**
   * `PumpSdk.setQuoteControlAdminInstruction` with `authority` defaulting to
   * the current `Global.authority`, the only key the program accepts.
   */
  async adminSetQuoteControlAdminInstruction({
    newAdmin,
    authority
  }) {
    return await PUMP_SDK.setQuoteControlAdminInstruction({
      authority: authority ?? (await this.fetchGlobal()).authority,
      newAdmin
    });
  }
  /**
   * `PumpSdk.addQuoteControlMintInstruction` with `authority` defaulting to
   * the current `Global.authority` (pass `QuoteControl.admin` to sign as the
   * delegated admin instead).
   */
  async adminAddQuoteControlMintInstruction({
    quoteMint,
    initialVirtualQuoteReserves,
    authority
  }) {
    return await PUMP_SDK.addQuoteControlMintInstruction({
      authority: authority ?? (await this.fetchGlobal()).authority,
      quoteMint,
      initialVirtualQuoteReserves
    });
  }
  /**
   * `PumpSdk.removeQuoteControlMintInstruction` with `authority` defaulting
   * to the current `Global.authority`.
   */
  async adminRemoveQuoteControlMintInstruction({
    quoteMint,
    authority
  }) {
    return await PUMP_SDK.removeQuoteControlMintInstruction({
      authority: authority ?? (await this.fetchGlobal()).authority,
      quoteMint
    });
  }
  /**
   * `PumpSdk.updateCreatorFeeConfigInstruction` with `authority` defaulting
   * to the current `Global.authority`, the only key the program accepts.
   */
  async adminUpdateCreatorFeeConfigInstruction({
    creatorFeeConfigurable,
    maxConfigurableCreatorFeeBps,
    authority
  }) {
    return await PUMP_SDK.updateCreatorFeeConfigInstruction({
      authority: authority ?? (await this.fetchGlobal()).authority,
      creatorFeeConfigurable,
      maxConfigurableCreatorFeeBps
    });
  }
  /**
   * `PumpSdk.setExoticFlatFeesInstruction` with `admin` defaulting to the
   * current `FeeConfig.admin`.
   */
  async adminSetExoticFlatFeesInstruction({
    exoticFlatFees,
    admin
  }) {
    return await PUMP_SDK.setExoticFlatFeesInstruction({
      admin: admin ?? (await this.fetchFeeConfig()).admin,
      exoticFlatFees
    });
  }
  async getCreatorVaultBalance(creator) {
    const creatorVault = creatorVaultPda(creator);
    const accountInfo = await this.connection.getAccountInfo(creatorVault);
    return await this.creatorVaultLamportsAboveRent(accountInfo);
  }
  async getCreatorVaultBalanceBothPrograms(creator) {
    const balance = await this.getCreatorVaultBalance(creator);
    const ammBalance = await this.pumpAmmSdk.getCoinCreatorVaultBalance(creator);
    return balance.add(ammBalance);
  }
  async adminUpdateTokenIncentives(startTime, endTime, dayNumber, tokenSupplyPerDay, secondsInADay = new import_bn3.default(86400), mint = PUMP_TOKEN_MINT, tokenProgram = import_spl_token2.TOKEN_2022_PROGRAM_ID) {
    const { authority } = await this.fetchGlobal();
    return await this.offlinePumpProgram.methods.adminUpdateTokenIncentives(
      startTime,
      endTime,
      secondsInADay,
      dayNumber,
      tokenSupplyPerDay
    ).accountsPartial({
      authority,
      mint,
      tokenProgram
    }).instruction();
  }
  async adminUpdateTokenIncentivesBothPrograms(startTime, endTime, dayNumber, tokenSupplyPerDay, secondsInADay = new import_bn3.default(86400), mint = PUMP_TOKEN_MINT, tokenProgram = import_spl_token2.TOKEN_2022_PROGRAM_ID) {
    return [
      await this.adminUpdateTokenIncentives(
        startTime,
        endTime,
        dayNumber,
        tokenSupplyPerDay,
        secondsInADay,
        mint,
        tokenProgram
      ),
      await this.pumpAmmAdminSdk.adminUpdateTokenIncentives(
        startTime,
        endTime,
        dayNumber,
        tokenSupplyPerDay,
        secondsInADay,
        mint,
        tokenProgram
      )
    ];
  }
  async claimTokenIncentives(user, payer) {
    const { mint } = await this.fetchGlobalVolumeAccumulator();
    if (mint.equals(import_web32.PublicKey.default)) {
      return [];
    }
    const [mintAccountInfo, userAccumulatorAccountInfo] = await this.connection.getMultipleAccountsInfo([
      mint,
      userVolumeAccumulatorPda(user)
    ]);
    if (!mintAccountInfo) {
      return [];
    }
    if (!userAccumulatorAccountInfo) {
      return [];
    }
    return [
      await this.offlinePumpProgram.methods.claimTokenIncentives().accountsPartial({
        user,
        payer,
        mint,
        tokenProgram: mintAccountInfo.owner
      }).instruction()
    ];
  }
  async claimTokenIncentivesBothPrograms(user, payer) {
    return [
      ...await this.claimTokenIncentives(user, payer),
      ...await this.pumpAmmSdk.claimTokenIncentives(user, payer)
    ];
  }
  async getTotalUnclaimedTokens(user) {
    const [
      globalVolumeAccumulatorAccountInfo,
      userVolumeAccumulatorAccountInfo
    ] = await this.connection.getMultipleAccountsInfo([
      GLOBAL_VOLUME_ACCUMULATOR_PDA,
      userVolumeAccumulatorPda(user)
    ]);
    if (!globalVolumeAccumulatorAccountInfo || !userVolumeAccumulatorAccountInfo) {
      return new import_bn3.default(0);
    }
    const globalVolumeAccumulator = PUMP_SDK.decodeGlobalVolumeAccumulator(
      globalVolumeAccumulatorAccountInfo
    );
    const userVolumeAccumulator = PUMP_SDK.decodeUserVolumeAccumulator(
      userVolumeAccumulatorAccountInfo
    );
    return totalUnclaimedTokens(globalVolumeAccumulator, userVolumeAccumulator);
  }
  async getTotalUnclaimedTokensBothPrograms(user) {
    return (await this.getTotalUnclaimedTokens(user)).add(
      await this.pumpAmmSdk.getTotalUnclaimedTokens(user)
    );
  }
  async getCurrentDayTokens(user) {
    const [
      globalVolumeAccumulatorAccountInfo,
      userVolumeAccumulatorAccountInfo
    ] = await this.connection.getMultipleAccountsInfo([
      GLOBAL_VOLUME_ACCUMULATOR_PDA,
      userVolumeAccumulatorPda(user)
    ]);
    if (!globalVolumeAccumulatorAccountInfo || !userVolumeAccumulatorAccountInfo) {
      return new import_bn3.default(0);
    }
    const globalVolumeAccumulator = PUMP_SDK.decodeGlobalVolumeAccumulator(
      globalVolumeAccumulatorAccountInfo
    );
    const userVolumeAccumulator = PUMP_SDK.decodeUserVolumeAccumulator(
      userVolumeAccumulatorAccountInfo
    );
    return currentDayTokens(globalVolumeAccumulator, userVolumeAccumulator);
  }
  async getCurrentDayTokensBothPrograms(user) {
    return (await this.getCurrentDayTokens(user)).add(
      await this.pumpAmmSdk.getCurrentDayTokens(user)
    );
  }
  async syncUserVolumeAccumulatorBothPrograms(user) {
    return [
      await PUMP_SDK.syncUserVolumeAccumulator(user),
      await import_pump_swap_sdk.PUMP_AMM_SDK.syncUserVolumeAccumulator(user)
    ];
  }
  /**
   * Gets the minimum distributable fee for a token's fee sharing configuration.
   *
   * This method handles both graduated (AMM) and non-graduated (bonding curve) tokens.
   * For graduated tokens, it automatically consolidates fees from the AMM vault before
   * calculating the minimum distributable fee.
   *
   * @param mint - The mint address of the token
   * @param simulationSigner - Optional signer address for transaction simulation.
   *                           Must have a non-zero SOL balance. Defaults to a known funded address.
   * @param options - Quote-mint-specific parameters. Without them the coin is
   *   treated as SOL-quoted, exactly as before these options existed.
   * @param options.quoteMint - The coin's quote mint (`bondingCurve.quoteMint`
   *   can be passed as is). Selects the canonical pool, so `isGraduated` is
   *   right for a non-SOL coin, and the consolidation instruction
   *   (`transferCreatorFeesToPumpV2`). Note that the on-chain
   *   `get_minimum_distributable_fee` view reads the lamport creator vault
   *   only, so for a non-SOL quote `minimumRequired`, `distributableFees` and
   *   `canDistribute` still describe SOL fees, not the quote-token fees (the
   *   consolidation moves tokens the view does not look at); the result's
   *   `feesQuoteMint` says which mint the figures are in. Use
   *   `getCreatorVaultQuoteBalances` for token-quote amounts.
   * @param options.quoteTokenProgram - The program that owns `quoteMint`;
   *   fetched from the mint when omitted for a non-SOL quote (one extra
   *   round-trip).
   * @param options.payer - Signer for the V2 consolidation instruction, which
   *   may initialize the pump vault ATA; defaults to `simulationSigner`.
   * @returns The minimum distributable fee information including whether distribution is possible
   */
  async getMinimumDistributableFee(mint, simulationSigner = new import_web32.PublicKey(
    "UqN2p5bAzBqYdHXcgB6WLtuVrdvmy9JSAtgqZb3CMKw"
  ), options = {}) {
    const quoteMint = normalizeQuoteMint(options.quoteMint);
    const isNativeQuote = quoteMint.equals(import_spl_token2.NATIVE_MINT);
    const quoteTokenProgram = options.quoteTokenProgram ?? (isNativeQuote ? import_spl_token2.TOKEN_PROGRAM_ID : await this.fetchQuoteTokenProgram(quoteMint));
    const payer = options.payer ?? simulationSigner;
    const sharingConfigPubkey = feeSharingConfigPda(mint);
    const poolAddress = canonicalPumpPoolPdaWithQuote(mint, quoteMint);
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk.coinCreatorVaultAuthorityPda)(sharingConfigPubkey);
    const ammVaultAta = (0, import_pump_swap_sdk.coinCreatorVaultAtaPda)(
      coinCreatorVaultAuthority,
      quoteMint,
      quoteTokenProgram
    );
    const [sharingConfigAccountInfo, poolAccountInfo, ammVaultAtaInfo] = await this.connection.getMultipleAccountsInfo([
      sharingConfigPubkey,
      poolAddress,
      ammVaultAta
    ]);
    if (!sharingConfigAccountInfo) {
      throw new Error(`Sharing config not found for mint: ${mint.toBase58()}`);
    }
    const sharingConfig = PUMP_SDK.decodeSharingConfig(
      sharingConfigAccountInfo
    );
    const instructions = [];
    const isGraduated = poolAccountInfo !== null;
    if (isGraduated && ammVaultAtaInfo) {
      const transferCreatorFeesToPumpIx = isNativeQuote ? await this.pumpAmmProgram.methods.transferCreatorFeesToPump().accountsPartial({
        wsolMint: import_spl_token2.NATIVE_MINT,
        tokenProgram: import_spl_token2.TOKEN_PROGRAM_ID,
        coinCreator: sharingConfigPubkey
      }).instruction() : await PUMP_SDK.transferCreatorFeesToPumpV2({
        payer,
        mint,
        quoteMint,
        quoteTokenProgram
      });
      instructions.push(transferCreatorFeesToPumpIx);
    }
    const getMinFeeIx = await PUMP_SDK.getMinimumDistributableFee({
      mint,
      sharingConfig,
      sharingConfigAddress: sharingConfigPubkey
    });
    instructions.push(getMinFeeIx);
    const { blockhash } = await this.connection.getLatestBlockhash();
    const tx = new import_web32.VersionedTransaction(
      new import_web32.TransactionMessage({
        payerKey: simulationSigner,
        recentBlockhash: blockhash,
        instructions
      }).compileToV0Message()
    );
    const result = await this.connection.simulateTransaction(tx);
    let minimumDistributableFee = {
      minimumRequired: new import_bn3.default(0),
      distributableFees: new import_bn3.default(0),
      canDistribute: false
    };
    if (!result.value.err) {
      const [data, encoding] = result.value.returnData?.data ?? [];
      if (data) {
        const buffer = Buffer.from(data, encoding);
        minimumDistributableFee = PUMP_SDK.decodeMinimumDistributableFee(buffer);
      }
    }
    return {
      ...minimumDistributableFee,
      isGraduated,
      // The only view the program has; a quote-aware one is a program change.
      feesQuoteMint: import_spl_token2.NATIVE_MINT
    };
  }
  /**
   * Gets the instructions to distribute creator fees for a token's fee sharing configuration.
   *
   * This method handles both graduated (AMM) and non-graduated (bonding curve) tokens.
   * For graduated tokens, it automatically includes an instruction to consolidate fees
   * from the AMM vault before distributing.
   *
   * @param mint - The mint address of the token
   * @param options - Optional quote-mint-specific parameters
   * @param options.quoteTokenProgram - The program that owns `quoteMint`.
   *   Fetched from the mint when omitted for a non-SOL quote (one extra
   *   round-trip before the account batch, which derives every ATA from it);
   *   `TOKEN_PROGRAM_ID` for SOL.
   * @param options.payer - Transaction signer. Required when `quoteMint` is not
   *   `NATIVE_MINT`: pays rent for the vault/shareholder ATAs the V2
   *   consolidation and distribution instructions may initialize.
   * @param options.quoteMint - The coin's quote mint
   * @returns The instructions to distribute creator fees and whether the token is graduated
   */
  async buildDistributeCreatorFeesInstructions(mint, options = {}) {
    const { payer } = options;
    const quoteMint = normalizeQuoteMint(options.quoteMint ?? import_spl_token2.NATIVE_MINT);
    const isNativeQuote = quoteMint.equals(import_spl_token2.NATIVE_MINT);
    if (!isNativeQuote && !payer) {
      throw new Error(
        "payer is required when quoteMint is not NATIVE_MINT (V2 instructions may initialize ATAs)"
      );
    }
    const quoteTokenProgram = options.quoteTokenProgram ?? (isNativeQuote ? import_spl_token2.TOKEN_PROGRAM_ID : await this.fetchQuoteTokenProgram(quoteMint));
    const sharingConfigPubkey = feeSharingConfigPda(mint);
    const poolAddress = canonicalPumpPoolPdaWithQuote(mint, quoteMint);
    const ammVaultAta = (0, import_pump_swap_sdk.coinCreatorVaultAtaPda)(
      (0, import_pump_swap_sdk.coinCreatorVaultAuthorityPda)(sharingConfigPubkey),
      quoteMint,
      quoteTokenProgram
    );
    const [sharingConfigAccountInfo, poolAccountInfo, ammVaultAtaInfo] = await this.connection.getMultipleAccountsInfo([
      sharingConfigPubkey,
      poolAddress,
      ammVaultAta
    ]);
    if (!sharingConfigAccountInfo) {
      throw new Error(`Sharing config not found for mint: ${mint.toBase58()}`);
    }
    const sharingConfig = PUMP_SDK.decodeSharingConfig(
      sharingConfigAccountInfo
    );
    const instructions = [];
    const isGraduated = poolAccountInfo !== null;
    if (isGraduated && ammVaultAtaInfo) {
      const transferCreatorFeesToPumpIx = isNativeQuote ? await this.pumpAmmProgram.methods.transferCreatorFeesToPump().accountsPartial({
        wsolMint: import_spl_token2.NATIVE_MINT,
        tokenProgram: import_spl_token2.TOKEN_PROGRAM_ID,
        coinCreator: sharingConfigPubkey
      }).instruction() : await PUMP_SDK.transferCreatorFeesToPumpV2({
        payer,
        mint,
        quoteMint,
        quoteTokenProgram
      });
      instructions.push(transferCreatorFeesToPumpIx);
    }
    const distributeCreatorFeesIx = isNativeQuote ? await PUMP_SDK.distributeCreatorFees({
      mint,
      sharingConfig,
      sharingConfigAddress: sharingConfigPubkey
    }) : await PUMP_SDK.distributeCreatorFeesV2({
      mint,
      sharingConfig,
      sharingConfigAddress: sharingConfigPubkey,
      quoteMint,
      payer,
      shouldInitializeAta: true,
      quoteTokenProgram
    });
    instructions.push(distributeCreatorFeesIx);
    return {
      instructions,
      isGraduated
    };
  }
};

// src/sdk.ts
function getPumpProgram(connection) {
  return new import_anchor.Program(
    pump_default,
    new import_anchor.AnchorProvider(connection, null, {})
  );
}
var PUMP_PROGRAM_ID = new import_web33.PublicKey(
  "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
);
function getPumpAmmProgram(connection) {
  return new import_anchor.Program(
    pump_amm_default,
    new import_anchor.AnchorProvider(connection, null, {})
  );
}
function getPumpFeeProgram(connection) {
  return new import_anchor.Program(
    pump_fees_default,
    new import_anchor.AnchorProvider(connection, null, {})
  );
}
var PUMP_AMM_PROGRAM_ID = new import_web33.PublicKey(
  "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
);
var MAYHEM_PROGRAM_ID = new import_web33.PublicKey(
  "MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e"
);
var PUMP_FEE_PROGRAM_ID = new import_web33.PublicKey(
  "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
);
var BONDING_CURVE_SIZE = 125;
var BONDING_CURVE_NEW_SIZE = 151;
var BONDING_CURVE_INITIALIZE_SIZE = 49;
var GLOBAL_SIZE = 1087;
var ADMIN_CTO_COMPUTE_UNIT_LIMIT = 6e5;
function zeroPadded(data, size) {
  return data.length >= size ? data : Buffer.concat([data, Buffer.alloc(size - data.length)]);
}
var CREATE_EVENT_LAYOUT_PADDINGS = [0, 1, 9];
var CREATE_POOL_EVENT_LAYOUT_PADDINGS = [0, 1, 10];
var TRADE_EVENT_LAYOUT_PADDINGS = [0, 16];
var FEE_CONFIG_INITIALIZE_SIZE = 2512;
var FEE_CONFIG_POST_STABLE_SIZE = 4073;
var FEE_CONFIG_CURRENT_SIZE = 4097;
var FEE_CONFIG_FEE_TIERS_OFFSET = 8 + 1 + 32 + 24;
var FEE_TIER_LEN = 16 + 24;
var FEES_LEN = 24;
var VEC_LEN_PREFIX = 4;
var MAX_FEE_TIERS_SUPPORTED = 50;
function feeTierVecEnd(data, offset) {
  const count = data.readUInt32LE(offset);
  const end = offset + VEC_LEN_PREFIX + count * FEE_TIER_LEN;
  if (count > MAX_FEE_TIERS_SUPPORTED || end > data.length) {
    throw new Error(
      `Invalid FeeConfig account: ${count} fee tiers declared at offset ${offset} in ${data.length} bytes`
    );
  }
  return end;
}
var QUOTE_CONTROL_HEADER_LEN = 8 + 32 + 64 + VEC_LEN_PREFIX;
var QUOTE_CONTROL_LEN_OFFSET = QUOTE_CONTROL_HEADER_LEN - VEC_LEN_PREFIX;
var QUOTE_CONTROL_ENTRY_LEN = 32 + 8;
function isRangeError(error) {
  return typeof error === "object" && error !== null && error.name === "RangeError";
}
function decodeWithTrailingDefaults(data, paddings, decode) {
  let rangeError;
  for (const padding of paddings) {
    try {
      return decode(Buffer.concat([data, Buffer.alloc(padding)]));
    } catch (error) {
      if (!isRangeError(error)) {
        throw error;
      }
      rangeError = error;
    }
  }
  throw rangeError;
}
function assertCreateV2FlagsAllowed({
  global,
  mint,
  cashback,
  holderReward,
  creatorFeeBps
}) {
  if (cashback) {
    throw new CashbackDeprecatedError(mint);
  }
  if (holderReward && !global.isHolderRewardEnabled) {
    throw new HolderRewardDisabledError();
  }
  if (!creatorFeeBps || creatorFeeBps.isZero()) {
    return;
  }
  if (!global.creatorFeeConfigurable) {
    throw new CreatorFeeNotConfigurableError();
  }
  if (creatorFeeBps.ltn(1) || creatorFeeBps.gt(global.maxConfigurableCreatorFeeBps)) {
    throw new CreatorFeeBpsOutOfRangeError(
      creatorFeeBps,
      global.maxConfigurableCreatorFeeBps
    );
  }
}
function createdCurveCreator(mint, creator, holderReward) {
  return holderReward ? holderRewardsPda(mint) : creator;
}
var PUMP_TOKEN_MINT = new import_web33.PublicKey(
  "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
);
var MAX_SHAREHOLDERS = 10;
var MIGRATE_FIXED_ACCOUNTS = 25;
var MIGRATE_V2_FIXED_ACCOUNTS = 27;
function assertBoostRemainingAccounts(instruction, fixedAccounts, boostVaultAuthority, boostVault) {
  const expectedLength = fixedAccounts + 2;
  if (instruction.keys.length !== expectedLength) {
    throw new Error(
      `migrate: expected ${expectedLength} accounts (${fixedAccounts} fixed + 2 boost), got ${instruction.keys.length}`
    );
  }
  if (!instruction.keys[fixedAccounts].pubkey.equals(boostVaultAuthority)) {
    throw new Error(
      `migrate: boost_vault_authority expected at index ${fixedAccounts}`
    );
  }
  if (!instruction.keys[fixedAccounts + 1].pubkey.equals(boostVault)) {
    throw new Error(
      `migrate: boost_vault expected at index ${fixedAccounts + 1}`
    );
  }
}
function createV2QuoteRemainingAccounts({
  mint,
  quoteMint,
  quoteTokenProgram
}) {
  return [
    { pubkey: quoteMint, isWritable: false, isSigner: false },
    {
      pubkey: quoteAta(bondingCurvePda(mint), quoteMint, quoteTokenProgram),
      isWritable: true,
      isSigner: false
    },
    { pubkey: quoteTokenProgram, isWritable: false, isSigner: false },
    { pubkey: QUOTE_CONTROL_PDA, isWritable: false, isSigner: false }
  ];
}
function createAndBuyQuote(quoteMint, quoteTokenProgram) {
  return quoteMint && !isLegacyQuoteMint(quoteMint) ? { buyQuoteMint: quoteMint, buyQuoteTokenProgram: quoteTokenProgram } : { buyQuoteMint: import_spl_token3.NATIVE_MINT, buyQuoteTokenProgram: import_spl_token3.TOKEN_PROGRAM_ID };
}
var DEFAULT_VAULT_QUOTE_CANDIDATES = Object.freeze([
  { mint: import_spl_token3.NATIVE_MINT, tokenProgram: import_spl_token3.TOKEN_PROGRAM_ID },
  {
    mint: new import_web33.PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    tokenProgram: import_spl_token3.TOKEN_PROGRAM_ID
  },
  {
    mint: new import_web33.PublicKey("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"),
    tokenProgram: import_spl_token3.TOKEN_PROGRAM_ID
  }
]);
var PumpSdk = class {
  constructor() {
    this.offlinePumpProgram = OFFLINE_PUMP_PROGRAM;
    this.offlinePumpFeeProgram = new import_anchor.Program(
      pump_fees_default,
      new import_anchor.AnchorProvider(null, null, {})
    );
    this.offlinePumpAmmProgram = new import_anchor.Program(
      pump_amm_default,
      new import_anchor.AnchorProvider(null, null, {})
    );
  }
  /**
   * Decodes the pump `Global` account, including the live 1045-byte account
   * that predates `creatorFeeConfigurable` / `maxConfigurableCreatorFeeBps`
   * (they read `false` / 0, see `GLOBAL_SIZE`).
   */
  decodeGlobal(accountInfo) {
    return this.offlinePumpProgram.coder.accounts.decode(
      "global",
      zeroPadded(accountInfo.data, GLOBAL_SIZE)
    );
  }
  /**
   * Decodes a pump-fees `FeeConfig` account the way the program does
   * (`FeeConfig::deserialize_versioned`): the account length selects the
   * layout version, and the bytes after that version's last field are never
   * read. `stableFeeTiers` is empty below `FEE_CONFIG_POST_STABLE_SIZE` and
   * `exoticFlatFees` is all-zero (unset) below `FEE_CONFIG_CURRENT_SIZE`,
   * whatever bytes follow the shorter layout (a pre-allocated tail, or stale
   * tier bytes left behind when a vector was upserted shorter). Throws on data
   * shorter than `FEE_CONFIG_INITIALIZE_SIZE` or a tier vector the program
   * could not have written.
   */
  decodeFeeConfig(accountInfo) {
    const { data } = accountInfo;
    if (data.length < FEE_CONFIG_INITIALIZE_SIZE) {
      throw new Error(
        `Invalid FeeConfig account: ${data.length} bytes, expected at least ${FEE_CONFIG_INITIALIZE_SIZE}`
      );
    }
    const feeTiersEnd = feeTierVecEnd(data, FEE_CONFIG_FEE_TIERS_OFFSET);
    let readEnd;
    if (data.length < FEE_CONFIG_POST_STABLE_SIZE) {
      readEnd = feeTiersEnd;
    } else {
      const stableFeeTiersEnd = feeTierVecEnd(data, feeTiersEnd);
      readEnd = data.length < FEE_CONFIG_CURRENT_SIZE ? stableFeeTiersEnd : stableFeeTiersEnd + FEES_LEN;
    }
    return this.offlinePumpProgram.coder.accounts.decode(
      "feeConfig",
      Buffer.concat([
        data.subarray(0, readEnd),
        Buffer.alloc(VEC_LEN_PREFIX + FEES_LEN)
      ])
    );
  }
  /**
   * Decodes a `BondingCurve` of every length the program has written (49, 81,
   * 82, 83, 115, 124 and the extended 151 bytes) the way its versioned reader
   * does: every layout is a prefix of the next and the fields a shorter
   * account lacks read as their defaults (the zero key, `false`, zero). Bytes
   * past `BONDING_CURVE_SIZE` (an extended curve) are ignored. Throws below
   * the 49-byte initial layout, as the program does. A length the program
   * never writes (say 100 bytes) is not special-cased: the program would read
   * it as the longest layout that fits and ignore the rest, this zero-padded
   * read takes the extra bytes as the start of the next field.
   */
  decodeBondingCurve(accountInfo) {
    const { data } = accountInfo;
    if (data.length < BONDING_CURVE_INITIALIZE_SIZE) {
      throw new Error(
        `Invalid BondingCurve account: ${data.length} bytes, expected at least ${BONDING_CURVE_INITIALIZE_SIZE}`
      );
    }
    return this.offlinePumpProgram.coder.accounts.decode(
      "bondingCurve",
      zeroPadded(data, BONDING_CURVE_SIZE)
    );
  }
  /**
   * The quote mint a pump-amm coin creator vault ATA holds, found by matching
   * the ATA against `candidates`.
   *
   * @param candidates - The quote mints to try, each with the program that
   *   owns it (the ATA is derived with it). Defaults to WSOL, mainnet USDC and
   *   devnet USDC under SPL Token. Quote-control mints and Token-2022 quotes
   *   are only found when passed here; build the list from
   *   `OnlinePumpSdk.fetchSupportedQuoteMints` plus each mint's
   *   `fetchQuoteTokenProgram` (or `resolveQuoteMint`).
   * @returns The matching mint, or `null` when no candidate matches.
   */
  getCoinCreatorVaultQuoteMint(coinCreator, coinCreatorVaultAta, candidates = DEFAULT_VAULT_QUOTE_CANDIDATES) {
    const vaultAuthority = ammCreatorVaultPda(coinCreator);
    for (const { mint, tokenProgram } of candidates) {
      const ata = (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        vaultAuthority,
        true,
        tokenProgram
      );
      if (ata.equals(coinCreatorVaultAta)) {
        return mint;
      }
    }
    return null;
  }
  decodeBondingCurveNullable(accountInfo) {
    try {
      return this.decodeBondingCurve(accountInfo);
    } catch (error) {
      console.warn("Failed to decode bonding curve", error);
      return null;
    }
  }
  /**
   * Decodes the pump `QuoteControl` PDA. Like the program's raw reader
   * (`QuoteControl::lookup_initial_virtual_quote_reserves`, error 6075
   * `InvalidQuoteControl`), the declared `mints` length must fit in the data;
   * bytes past it (the pre-allocated tail, or stale entries left behind by a
   * remove) are ignored. The program never writes an over-declared account
   * (it grows before it pushes and never shrinks), so this only rejects
   * corrupt or foreign data, which would otherwise decode as phantom zero-key
   * entries or, for a huge count, allocate until the process dies.
   */
  decodeQuoteControl(accountInfo) {
    const { data } = accountInfo;
    if (data.length < QUOTE_CONTROL_HEADER_LEN) {
      throw new Error(
        `Invalid QuoteControl account: ${data.length} bytes, expected at least ${QUOTE_CONTROL_HEADER_LEN}`
      );
    }
    const count = data.readUInt32LE(QUOTE_CONTROL_LEN_OFFSET);
    if (QUOTE_CONTROL_HEADER_LEN + count * QUOTE_CONTROL_ENTRY_LEN > data.length) {
      throw new Error(
        `Invalid QuoteControl account: ${count} entries declared in ${data.length} bytes`
      );
    }
    return this.offlinePumpProgram.coder.accounts.decode(
      "quoteControl",
      data
    );
  }
  /**
   * `null` when the account is missing (the PDA is not initialized yet, which
   * the program treats as an empty list) or does not decode as a
   * `QuoteControl` (wrong discriminator, over-declared length; logged with
   * `console.warn`). Note that `OnlinePumpSdk.fetchQuoteControl` is stricter:
   * it returns `null` only for a missing account and throws on a malformed
   * one.
   */
  decodeQuoteControlNullable(accountInfo) {
    if (!accountInfo) {
      return null;
    }
    try {
      return this.decodeQuoteControl(accountInfo);
    } catch (error) {
      console.warn("Failed to decode quote control", error);
      return null;
    }
  }
  decodeGlobalVolumeAccumulator(accountInfo) {
    return this.offlinePumpProgram.coder.accounts.decode(
      "globalVolumeAccumulator",
      accountInfo.data
    );
  }
  decodeUserVolumeAccumulator(accountInfo) {
    return this.offlinePumpProgram.coder.accounts.decode(
      "userVolumeAccumulator",
      accountInfo.data
    );
  }
  decodeUserVolumeAccumulatorNullable(accountInfo) {
    try {
      return this.decodeUserVolumeAccumulator(accountInfo);
    } catch (error) {
      console.warn("Failed to decode user volume accumulator", error);
      return null;
    }
  }
  decodeSharingConfig(accountInfo) {
    return this.offlinePumpFeeProgram.coder.accounts.decode(
      "sharingConfig",
      accountInfo.data
    );
  }
  decodeSocialFeePda(accountInfo) {
    return this.offlinePumpFeeProgram.coder.accounts.decode(
      "socialFeePda",
      accountInfo.data
    );
  }
  decodeSocialFeePdaClaimedEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "socialFeePdaClaimed",
      data
    );
  }
  decodeSocialFeePdaCreatedEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "socialFeePdaCreated",
      data
    );
  }
  decodeCreateFeeSharingConfigEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "createFeeSharingConfigEvent",
      data
    );
  }
  decodeUpdateFeeSharesEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "updateFeeSharesEvent",
      data
    );
  }
  decodeUpdateAdminEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "updateAdminEvent",
      data
    );
  }
  decodeSetAuthorityEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "setAuthorityEvent",
      data
    );
  }
  decodeResetFeeSharingConfigEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "resetFeeSharingConfigEvent",
      data
    );
  }
  decodeDonationFeePdaCreatedEvent(data) {
    return this.offlinePumpFeeProgram.coder.types.decode(
      "donationFeePdaCreated",
      data
    );
  }
  decodeCollectCreatorFeeEventBc(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "collectCreatorFeeEvent",
      data
    );
  }
  decodeCollectCoinCreatorFeeEventAmm(data) {
    return this.offlinePumpAmmProgram.coder.types.decode(
      "collectCoinCreatorFeeEvent",
      data
    );
  }
  /**
   * Decodes a pump-amm `CreatePoolEvent` emitted under any layout. The
   * vendored IDL ends the event with `creator_fee_bps: u64`,
   * `can_edit_creator_fee: bool` (configurable creator fees) and
   * `is_holder_reward: bool` (holder-reward coins); the program deployed
   * before the last emits it one byte shorter, the one before the other two
   * ten bytes shorter. The borsh coder rejects either with a RangeError, so
   * the event is retried with the missing fields' defaults appended
   * (`creatorFeeBps` zero, `canEditCreatorFee` / `isHolderReward` false). An
   * event shorter than the oldest layout still throws.
   */
  decodeCreatePoolEventAmm(data) {
    return decodeWithTrailingDefaults(
      data,
      CREATE_POOL_EVENT_LAYOUT_PADDINGS,
      (bytes) => this.offlinePumpAmmProgram.coder.types.decode(
        "createPoolEvent",
        bytes
      )
    );
  }
  decodeDepositEventAmm(data) {
    return this.offlinePumpAmmProgram.coder.types.decode(
      "depositEvent",
      data
    );
  }
  decodeWithdrawEventAmm(data) {
    return this.offlinePumpAmmProgram.coder.types.decode(
      "withdrawEvent",
      data
    );
  }
  /**
   * Decodes a pump-amm `BuyEvent` emitted under either layout: the vendored
   * IDL ends it with `holder_rewards_bps` / `holder_rewards` (holder-reward
   * coins); an event from the program deployed before them decodes with both
   * zero.
   */
  decodeBuyEventAmm(data) {
    return decodeWithTrailingDefaults(
      data,
      TRADE_EVENT_LAYOUT_PADDINGS,
      (bytes) => this.offlinePumpAmmProgram.coder.types.decode(
        "buyEvent",
        bytes
      )
    );
  }
  /** Like `decodeBuyEventAmm`, for `SellEvent`. */
  decodeSellEventAmm(data) {
    return decodeWithTrailingDefaults(
      data,
      TRADE_EVENT_LAYOUT_PADDINGS,
      (bytes) => this.offlinePumpAmmProgram.coder.types.decode(
        "sellEvent",
        bytes
      )
    );
  }
  decodeAdminCtoPoolEventAmm(data) {
    return this.offlinePumpAmmProgram.coder.types.decode(
      "adminCtoPoolEvent",
      data
    );
  }
  /**
   * Decodes a bonding-curve `CreateEvent` emitted under any deployment's
   * layout. The vendored IDL ends the event with `creator_fee_bps: u64`
   * (configurable creator fees) then `is_holder_reward: bool` (holder-reward
   * coins). A program without the last field emits the event one byte
   * shorter, one without both nine bytes shorter; the borsh coder rejects
   * either with a RangeError, so the event is retried with the missing
   * fields' encodings appended, shortest padding first. A missing field
   * decodes as its default: `creatorFeeBps` zero, `isHolderReward` false. An
   * event truncated inside a field still throws.
   */
  decodeCreateEventBc(data) {
    return decodeWithTrailingDefaults(
      data,
      CREATE_EVENT_LAYOUT_PADDINGS,
      (bytes) => this.offlinePumpProgram.coder.types.decode(
        "createEvent",
        bytes
      )
    );
  }
  /**
   * Decodes a bonding-curve `TradeEvent` emitted under either layout: the
   * vendored IDL ends it with `holder_rewards_bps` / `holder_rewards`
   * (holder-reward coins); an event from the program deployed before them
   * decodes with both zero.
   */
  decodeTradeEventBc(data) {
    return decodeWithTrailingDefaults(
      data,
      TRADE_EVENT_LAYOUT_PADDINGS,
      (bytes) => this.offlinePumpProgram.coder.types.decode(
        "tradeEvent",
        bytes
      )
    );
  }
  decodeCompleteEventBc(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "completeEvent",
      data
    );
  }
  decodeAdminCtoEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "adminCtoEvent",
      data
    );
  }
  decodeDistributeFeeToHoldersEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "distributeFeeToHoldersEvent",
      data
    );
  }
  decodeSetQuoteControlAdminEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "setQuoteControlAdminEvent",
      data
    );
  }
  decodeAddQuoteControlMintEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "addQuoteControlMintEvent",
      data
    );
  }
  decodeRemoveQuoteControlMintEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "removeQuoteControlMintEvent",
      data
    );
  }
  decodeUpdateCreatorFeeConfigEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "updateCreatorFeeConfigEvent",
      data
    );
  }
  decodeClaimCashbackEventBc(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "claimCashbackEvent",
      data
    );
  }
  decodeClaimCashbackEventAmm(data) {
    return this.offlinePumpAmmProgram.coder.types.decode(
      "claimCashbackEvent",
      data
    );
  }
  decodeDonationFeePda(accountInfo) {
    return this.offlinePumpFeeProgram.coder.accounts.decode(
      "donationFeePda",
      accountInfo.data
    );
  }
  /**
   * @deprecated Use `createV2Instruction` instead.
   */
  async createInstruction({
    mint,
    name,
    symbol,
    uri,
    creator,
    user
  }) {
    return await this.offlinePumpProgram.methods.create(name, symbol, uri, creator).accountsPartial({
      mint,
      user,
      tokenProgram: import_spl_token3.TOKEN_PROGRAM_ID
    }).instruction();
  }
  /**
   * Builds `create_v2`. Without `quoteMint` (or with legacy WSOL / the zero
   * key) the curve is quoted in SOL and the instruction is unchanged from
   * earlier SDK versions. Any other `quoteMint` must be whitelisted on
   * `Global` or listed in the `QuoteControl` PDA
   * (`OnlinePumpSdk.fetchSupportedQuoteMints`) and is selected by four
   * positional remaining accounts: [0] the quote mint (read-only), [1] the
   * bonding curve's quote ATA derived under `quoteTokenProgram` (writable; the
   * program creates it), [2] `quoteTokenProgram` (read-only), [3] the
   * `QuoteControl` PDA (`QUOTE_CONTROL_PDA`, read-only). The PDA is always
   * sent: the program reads it only for a mint `Global` does not whitelist,
   * and the program deployed before quote control ignores a fourth account.
   *
   * A mint admitted only through quote control cannot be combined with
   * `mayhemMode` (6071 `MayhemModeQuoteMintNotAllowed`). Token-quoted creates
   * are heavy (a mayhem create with a token quote ~200-240k CU, the first
   * `buy_v2` on a Token-2022 quote ~200-220k), so add an explicit
   * `ComputeBudgetProgram.setComputeUnitLimit`: ~500k for create + buy with a
   * token quote, ~250-300k for a standalone `buy_v2` / `sell_v2` on a
   * Token-2022 quote.
   *
   * @param params.quoteTokenProgram - The program that owns `quoteMint`
   *   (`TOKEN_PROGRAM_ID` or `TOKEN_2022_PROGRAM_ID`); the program rejects a
   *   mismatch with 6063 `UnsupportedQuoteMint`. Defaults to
   *   `TOKEN_PROGRAM_ID`, which is right for USDC; resolve it with
   *   `OnlinePumpSdk.fetchQuoteTokenProgram` for anything else. Ignored for
   *   SOL.
   * @param params.creatorFeeBps - The coin's own creator fee rate in basis
   *   points (see `BondingCurve.creatorFeeBps`). Omitted or zero means the
   *   pump-fees schedule rate. Always encoded as the 8-byte `creator_fee_bps`
   *   argument, zero when unset. A nonzero rate needs
   *   `Global.creatorFeeConfigurable` and
   *   `1..=Global.maxConfigurableCreatorFeeBps` (6077 / 6078), and only a
   *   quote admitted through `QuoteControl` stores it (on SOL or USDC it is
   *   ignored); this builder encodes what it is given and leaves the program
   *   to judge. Quote the first buy with the same rate
   *   (`getBuyTokenAmountFromSolAmount`'s `creatorFeeBps`). The rate changes
   *   afterwards only through a CTO (`adminCtoInstruction`).
   * @param params.holderReward - Creates a holder-reward coin: the program
   *   ignores `creator` and makes the coin's `holderRewardsPda(mint)` the
   *   creator, so every creator fee accrues to that PDA's vault and is paid
   *   out to holders through `distribute_fee_to_holders`. Permanent. Always
   *   encoded as the trailing 1-byte `is_holder_reward` argument, `false`
   *   when unset: the program deployed before holder-reward coins ignores
   *   trailing instruction bytes, the new one reads them. Needs
   *   `Global.isHolderRewardEnabled` (6084). The first buy's creator vault
   *   must then be the PDA's: the create-and-buy builders handle it.
   * @param params.cashback - Deprecated. `create_v2` rejects `true` with 6082
   *   `CashbackDeprecated`; existing cashback coins are unaffected. Still
   *   encoded as given so the instruction bytes stay predictable.
   */
  async createV2Instruction({
    mint,
    name,
    symbol,
    uri,
    creator,
    user,
    mayhemMode,
    cashback = false,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    creatorFeeBps,
    holderReward = false
  }) {
    const builder = this.offlinePumpProgram.methods.createV2(
      name,
      symbol,
      uri,
      creator,
      mayhemMode,
      [cashback ?? false],
      [new import_bn4.default(creatorFeeBps ?? 0)],
      [holderReward ?? false]
    ).accountsPartial({
      mint,
      user,
      tokenProgram: import_spl_token3.TOKEN_2022_PROGRAM_ID,
      mayhemProgramId: MAYHEM_PROGRAM_ID,
      globalParams: getGlobalParamsPda(),
      solVault: getSolVaultPda(),
      mayhemState: getMayhemStatePda(mint),
      mayhemTokenVault: getTokenVaultPda(mint)
    });
    if (quoteMint && !isLegacyQuoteMint(quoteMint)) {
      return await builder.remainingAccounts(
        createV2QuoteRemainingAccounts({
          mint,
          quoteMint,
          quoteTokenProgram
        })
      ).instruction();
    }
    return await builder.instruction();
  }
  async buyInstructions({
    global,
    bondingCurveAccountInfo,
    bondingCurve,
    associatedUserAccountInfo,
    mint,
    user,
    amount,
    solAmount,
    slippage,
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const instructions = [];
    const associatedUser = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      user,
      true,
      tokenProgram
    );
    if (!associatedUserAccountInfo) {
      instructions.push(
        (0, import_spl_token3.createAssociatedTokenAccountIdempotentInstruction)(
          user,
          associatedUser,
          user,
          mint,
          tokenProgram
        )
      );
    }
    instructions.push(
      await this.buyInstruction({
        global,
        mint,
        creator: bondingCurve.creator,
        user,
        associatedUser,
        amount,
        solAmount,
        slippage,
        tokenProgram,
        mayhemMode: bondingCurve.isMayhemMode
      })
    );
    return instructions;
  }
  /**
   * `create_v2` + the user's base ATA + a first legacy `buy`, SOL-quoted.
   *
   * @param params.creatorFeeBps - Forwarded to `createV2Instruction`. Unlike
   *   that builder this one holds `global`, so a nonzero rate the program
   *   would reject throws up front: `CreatorFeeNotConfigurableError` (gate
   *   off), `CreatorFeeBpsOutOfRangeError` (outside
   *   `1..=global.maxConfigurableCreatorFeeBps`). Quote `amount` with the same
   *   rate (`getBuyTokenAmountFromSolAmount`'s `creatorFeeBps`), or the buy's
   *   `solAmount` falls short of the fees the program charges.
   * @param params.holderReward - Forwarded to `createV2Instruction`; the buy
   *   then targets the holder-rewards PDA's creator vault, as the program
   *   does. Throws `HolderRewardDisabledError` while
   *   `global.isHolderRewardEnabled` is off.
   * @param params.cashback - Deprecated: throws `CashbackDeprecatedError`
   *   when `true`, as `create_v2` would fail with 6082.
   */
  async createV2AndBuyInstructions({
    global,
    mint,
    name,
    symbol,
    uri,
    creator,
    user,
    amount,
    solAmount,
    mayhemMode,
    cashback,
    isTokenizedAgent = false,
    buyBackBps = 0,
    creatorFeeBps,
    holderReward = false
  }) {
    assertCreateV2FlagsAllowed({
      global,
      mint,
      cashback,
      holderReward,
      creatorFeeBps
    });
    const associatedUser = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      user,
      true,
      import_spl_token3.TOKEN_2022_PROGRAM_ID
    );
    const buyInstruction = await this.buyInstruction({
      global,
      mint,
      creator: createdCurveCreator(mint, creator, holderReward),
      user,
      associatedUser,
      amount,
      solAmount,
      slippage: 1,
      tokenProgram: import_spl_token3.TOKEN_2022_PROGRAM_ID,
      mayhemMode
    });
    const instructions = [
      await this.createV2Instruction({
        mint,
        name,
        symbol,
        uri,
        creator,
        user,
        mayhemMode,
        cashback,
        creatorFeeBps,
        holderReward
      }),
      (0, import_spl_token3.createAssociatedTokenAccountIdempotentInstruction)(
        user,
        associatedUser,
        user,
        mint,
        import_spl_token3.TOKEN_2022_PROGRAM_ID
      ),
      buyInstruction
    ];
    if (isTokenizedAgent) {
      const agentPaymentsSdk = import_agent_payments_sdk.PumpAgentOffline.load(mint);
      const agentInitializeIx = await agentPaymentsSdk.create({
        authority: creator,
        mint,
        agentAuthority: creator,
        buybackBps: buyBackBps
      });
      instructions.push(agentInitializeIx);
    }
    return instructions;
  }
  /**
   * @deprecated Use `createV2AndBuyInstructions` instead.
   */
  async createAndBuyInstructions({
    global,
    mint,
    name,
    symbol,
    uri,
    creator,
    user,
    amount,
    solAmount,
    isTokenizedAgent = false,
    buyBackBps = 0
  }) {
    const associatedUser = (0, import_spl_token3.getAssociatedTokenAddressSync)(mint, user, true);
    const buyInstruction = await this.buyInstruction({
      global,
      mint,
      creator,
      user,
      associatedUser,
      amount,
      solAmount,
      slippage: 1,
      tokenProgram: import_spl_token3.TOKEN_PROGRAM_ID,
      mayhemMode: false
    });
    const instructions = [
      await this.createInstruction({ mint, name, symbol, uri, creator, user }),
      (0, import_spl_token3.createAssociatedTokenAccountIdempotentInstruction)(
        user,
        associatedUser,
        user,
        mint
      ),
      buyInstruction
    ];
    if (isTokenizedAgent) {
      const agentPaymentsSdk = import_agent_payments_sdk.PumpAgentOffline.load(mint);
      const agentInitializeIx = await agentPaymentsSdk.create({
        authority: creator,
        mint,
        agentAuthority: creator,
        buybackBps: buyBackBps
      });
      instructions.push(agentInitializeIx);
    }
    return instructions;
  }
  async buyInstruction({
    global,
    mint,
    creator,
    user,
    associatedUser,
    amount,
    solAmount,
    slippage,
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    mayhemMode = false
  }) {
    return await this.getBuyInstructionInternal({
      user,
      associatedUser,
      mint,
      creator,
      feeRecipient: getFeeRecipient(global, mayhemMode),
      buybackFeeRecipient: getStaticRandomFeeRecipientForBuyback(),
      amount,
      solAmount: solAmount.add(
        solAmount.mul(new import_bn4.default(Math.floor(slippage * 10))).div(new import_bn4.default(1e3))
      ),
      tokenProgram
    });
  }
  async sellInstructions({
    global,
    bondingCurveAccountInfo,
    bondingCurve,
    mint,
    user,
    amount,
    solAmount,
    slippage,
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    mayhemMode = false,
    cashback = false
  }) {
    const instructions = [];
    instructions.push(
      await this.getSellInstructionInternal({
        user,
        mint,
        creator: bondingCurve.creator,
        feeRecipient: getFeeRecipient(global, mayhemMode),
        buybackFeeRecipient: getStaticRandomFeeRecipientForBuyback(),
        amount,
        solAmount: solAmount.sub(
          solAmount.mul(new import_bn4.default(Math.floor(slippage * 10))).div(new import_bn4.default(1e3))
        ),
        tokenProgram,
        cashback
      })
    );
    return instructions;
  }
  async extendAccountInstruction({
    account,
    user
  }) {
    return this.offlinePumpProgram.methods.extendAccount().accountsPartial({
      account,
      user
    }).instruction();
  }
  async migrateInstruction({
    withdrawAuthority,
    mint,
    user,
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const bondingCurve = bondingCurvePda(mint);
    const associatedBondingCurve = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      bondingCurve,
      true,
      tokenProgram
    );
    const poolAuthority = pumpPoolAuthorityPda(mint);
    const poolAuthorityMintAccount = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      poolAuthority,
      true,
      tokenProgram
    );
    const pool = canonicalPumpPoolPda(mint);
    const poolBaseTokenAccount = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      pool,
      true,
      tokenProgram
    );
    const boostVaultAuthority = boostVaultAuthorityPda(pool);
    const boostVault = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      import_spl_token3.NATIVE_MINT,
      boostVaultAuthority,
      true,
      import_spl_token3.TOKEN_PROGRAM_ID
    );
    const instruction = await this.offlinePumpProgram.methods.migrate().accountsPartial({
      mint,
      user,
      withdrawAuthority,
      associatedBondingCurve,
      poolAuthorityMintAccount,
      poolBaseTokenAccount
    }).remainingAccounts([
      { pubkey: boostVaultAuthority, isWritable: false, isSigner: false },
      { pubkey: boostVault, isWritable: true, isSigner: false }
    ]).instruction();
    assertBoostRemainingAccounts(
      instruction,
      MIGRATE_FIXED_ACCOUNTS,
      boostVaultAuthority,
      boostVault
    );
    return instruction;
  }
  /**
   * @param params.quoteMint - The curve's quote mint; `bondingCurve.quoteMint`
   *   can be passed as is. `migrate_v2` accepts the mint the curve stores or,
   *   for a SOL curve (which stores the zero key), legacy WSOL, and the pool
   *   and every quote ATA are derived from WSOL in that case, so the zero key
   *   and `undefined` are normalized to `NATIVE_MINT`.
   * @param params.quoteTokenProgram - The program that owns `quoteMint`; all
   *   quote-side ATAs are derived with it. Defaults to `TOKEN_PROGRAM_ID`
   *   (SOL, USDC); pass `TOKEN_2022_PROGRAM_ID` for a Token-2022 quote.
   */
  async migrateV2Instruction({
    withdrawAuthority,
    mint,
    user,
    quoteMint: quoteMintOrDefault,
    baseTokenProgram = import_spl_token3.TOKEN_2022_PROGRAM_ID,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const quoteMint = normalizeQuoteMint(quoteMintOrDefault);
    const bondingCurve = bondingCurvePda(mint);
    const poolAuthority = pumpPoolAuthorityPda(mint);
    const poolAuthorityMintAccount = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      poolAuthority,
      true,
      baseTokenProgram
    );
    const pool = canonicalPumpPoolPdaWithQuote(mint, quoteMint);
    const poolBaseTokenAccount = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      pool,
      true,
      baseTokenProgram
    );
    const associatedBaseBondingCurve = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      bondingCurve,
      true,
      baseTokenProgram
    );
    const associatedQuoteBondingCurve = quoteAta(
      bondingCurve,
      quoteMint,
      quoteTokenProgram
    );
    const poolAuthorityQuoteAccount = quoteAta(
      poolAuthority,
      quoteMint,
      quoteTokenProgram
    );
    const poolQuoteTokenAccount = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      quoteMint,
      pool,
      true,
      quoteTokenProgram
    );
    const boostVaultAuthority = boostVaultAuthorityPda(pool);
    const boostVault = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      quoteMint,
      boostVaultAuthority,
      true,
      quoteTokenProgram
    );
    const instruction = await this.offlinePumpProgram.methods.migrateV2().accountsPartial({
      baseMint: mint,
      quoteMint,
      user,
      withdrawAuthority,
      bondingCurve,
      poolAuthorityMintAccount,
      poolBaseTokenAccount,
      pool,
      poolAuthority,
      systemProgram: import_web33.SystemProgram.programId,
      pumpAmm: PUMP_AMM_PROGRAM_ID,
      pumpAmmEventAuthority: getEventAuthorityPda(PUMP_AMM_PROGRAM_ID),
      eventAuthority: getEventAuthorityPda(PUMP_PROGRAM_ID),
      program: PUMP_PROGRAM_ID,
      associatedBaseBondingCurve,
      associatedQuoteBondingCurve,
      poolAuthorityQuoteAccount,
      poolQuoteTokenAccount,
      baseTokenProgram,
      quoteTokenProgram
    }).remainingAccounts([
      { pubkey: boostVaultAuthority, isWritable: false, isSigner: false },
      { pubkey: boostVault, isWritable: true, isSigner: false }
    ]).instruction();
    assertBoostRemainingAccounts(
      instruction,
      MIGRATE_V2_FIXED_ACCOUNTS,
      boostVaultAuthority,
      boostVault
    );
    return instruction;
  }
  async syncUserVolumeAccumulator(user) {
    return await this.offlinePumpProgram.methods.syncUserVolumeAccumulator().accountsPartial({ user }).instruction();
  }
  async setCreator({
    mint,
    setCreatorAuthority,
    creator
  }) {
    return await this.offlinePumpProgram.methods.setCreator(creator).accountsPartial({
      mint,
      setCreatorAuthority
    }).instruction();
  }
  async initUserVolumeAccumulator({
    payer,
    user
  }) {
    return await this.offlinePumpProgram.methods.initUserVolumeAccumulator().accountsPartial({ payer, user }).instruction();
  }
  async closeUserVolumeAccumulator(user) {
    return await this.offlinePumpProgram.methods.closeUserVolumeAccumulator().accountsPartial({ user }).instruction();
  }
  /**
   * `initialize_quote_control`: creates the `QuoteControl` PDA
   * (`QUOTE_CONTROL_PDA`) with no admin and an empty mint list. Permissionless
   * and once only (a second call fails in the system program, so nobody can
   * reset the list); `user` signs and pays the rent for the initial 2108
   * bytes. Only `Global.authority` can then assign an admin via
   * `setQuoteControlAdminInstruction`.
   */
  async initializeQuoteControlInstruction({
    user
  }) {
    return await this.offlinePumpProgram.methods.initializeQuoteControl().accountsPartial({ user }).instruction();
  }
  /**
   * `set_quote_control_admin`: `authority` must sign and be `Global.authority`.
   * The zero key revokes the admin, after which only `Global.authority` can
   * change the list.
   */
  async setQuoteControlAdminInstruction({
    authority,
    newAdmin
  }) {
    return await this.offlinePumpProgram.methods.setQuoteControlAdmin(newAdmin).accountsPartial({ authority }).instruction();
  }
  /**
   * `add_quote_control_mint`: lists `quoteMint` as a `create_v2` quote, with
   * the `virtualQuoteReserves` a new curve quoted in it starts from (stored as
   * given, in the mint's base units). `authority` signs and must be
   * `QuoteControl.admin` or `Global.authority`; it pays the rent top-up when
   * the list grows past the 50 pre-allocated entries. The program rejects the
   * zero key, WSOL and the Token-2022 native mint (6069), a mint already
   * listed (6067; change its reserves with remove + add) and a full list of
   * 256 (6066). A mint `Global` whitelists may be listed too but keeps
   * `Global.initialVirtualQuoteReserves`.
   */
  async addQuoteControlMintInstruction({
    authority,
    quoteMint,
    initialVirtualQuoteReserves
  }) {
    return await this.offlinePumpProgram.methods.addQuoteControlMint(quoteMint, initialVirtualQuoteReserves).accountsPartial({ authority }).instruction();
  }
  /**
   * `remove_quote_control_mint`: de-lists `quoteMint` (6068 when it is not
   * listed). Same signer rule as `addQuoteControlMintInstruction`. Existing
   * curves quoted in the mint keep trading; only new `create_v2` calls are
   * refused.
   */
  async removeQuoteControlMintInstruction({
    authority,
    quoteMint
  }) {
    return await this.offlinePumpProgram.methods.removeQuoteControlMint(quoteMint).accountsPartial({ authority }).instruction();
  }
  /**
   * `update_creator_fee_config`: turns per-coin creator fees on or off and
   * sets the ceiling a coin may configure (`Global.creatorFeeConfigurable`,
   * `Global.maxConfigurableCreatorFeeBps`). `authority` signs and must be
   * `Global.authority`. The program puts no bound on the ceiling: a rate that
   * pushes protocol + creator fees past 100% makes a coin buy-only. With the
   * gate off, configured rates are neither read nor accepted (kill switch).
   * Fails on the live 1045-byte `Global` until `extend_account` grows it to
   * `GLOBAL_SIZE`.
   */
  async updateCreatorFeeConfigInstruction({
    authority,
    creatorFeeConfigurable,
    maxConfigurableCreatorFeeBps
  }) {
    return await this.offlinePumpProgram.methods.updateCreatorFeeConfig(
      creatorFeeConfigurable,
      maxConfigurableCreatorFeeBps
    ).accountsPartial({ authority }).instruction();
  }
  /**
   * `update_holder_reward_config`: turns holder-reward coin creation (and CTO
   * holder conversion) on or off and names the one signer
   * `distribute_fee_to_holders` accepts (`Global.isHolderRewardEnabled`,
   * `Global.holderRewardClaimAuthority`). `authority` signs and must be
   * `Global.authority`. Fails on a `Global` shorter than `GLOBAL_SIZE` until
   * `extend_account` grows it.
   */
  async updateHolderRewardConfigInstruction({
    authority,
    isHolderRewardEnabled,
    holderRewardClaimAuthority
  }) {
    return await this.offlinePumpProgram.methods.updateHolderRewardConfig(
      isHolderRewardEnabled,
      holderRewardClaimAuthority
    ).accountsPartial({ authority }).instruction();
  }
  /**
   * `admin_cto`, the one community-takeover instruction: re-points where a
   * coin's creator fees go on the bonding curve, its canonical pump-amm pool
   * (through `admin_cto_pool`, when one exists) and its pump-fees
   * `SharingConfig` (through `admin_cto_sharing_config`, when the coin is
   * fee-shared), in one transaction. `adminSetCreatorAuthority` signs, must
   * be `Global.adminSetCreatorAuthority`, and pays the rent that grows a
   * pre-upgrade curve or pool and any ATA created. Budget
   * `ADMIN_CTO_COMPUTE_UNIT_LIMIT` compute units.
   *
   * Two paths, chosen by the arguments (the program rejects the rest):
   * - **new creator**: `newCreator` set, `isHolderReward` unset or `false`.
   *   The outgoing wallet creator is first paid from both vaults; a
   *   fee-shared coin keeps its SharingConfig as creator and the config is
   *   rewritten to `newCreator` at 100%.
   * - **holder rewards**: `isHolderReward: true`, no `newCreator`. The
   *   creator becomes `holderRewardsPda(mint)`, cashback is cleared, a
   *   fee-shared coin's vaults are swept into that PDA's creator vault and
   *   its SharingConfig is terminated. Permanent: a later CTO on the coin may
   *   only repeat this path to change the rate (6083 otherwise). Needs
   *   `Global.isHolderRewardEnabled` (6084).
   *
   * `creatorFeeBps` may be set on either path, only on a quote admitted
   * through `QuoteControl` (6091 on SOL or a whitelisted quote), within
   * `1..=Global.maxConfigurableCreatorFeeBps` with the gate on (6078 / 6077),
   * and not on a coin that stays cashback (6080). Mayhem coins are refused
   * (6088). This builder encodes what it is given;
   * `OnlinePumpSdk.adminCtoInstructions` resolves the accounts from chain and
   * checks these rules up front.
   *
   * @param params.currentCreator - `bondingCurve.creator` as stored (the zero
   *   key on a legacy curve, the SharingConfig PDA on a fee-shared coin, the
   *   holder-rewards PDA on a holder-reward coin). Marked writable unless it
   *   is the zero key, so a wallet creator can be paid (6092 otherwise).
   * @param params.quoteMint - The curve's quote mint, `NATIVE_MINT` for a
   *   SOL-quoted or legacy curve (the program accepts WSOL for a curve that
   *   stores the zero key). Every quote ATA and the pool address derive from
   *   it and `quoteTokenProgram`, the program that owns the mint.
   */
  async adminCtoInstruction({
    adminSetCreatorAuthority,
    mint,
    currentCreator,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    isHolderReward,
    creatorFeeBps,
    newCreator
  }) {
    const creatorVault = creatorVaultPda(currentCreator);
    const holderCreatorVault = creatorVaultPda(holderRewardsPda(mint));
    const coinCreatorVaultAuthority = ammCreatorVaultPda(currentCreator);
    const ata = (owner) => quoteAta(owner, quoteMint, quoteTokenProgram);
    const instruction = await this.offlinePumpProgram.methods.adminCto(
      isHolderReward ?? null,
      creatorFeeBps ?? null,
      newCreator ?? null
    ).accountsPartial({
      adminSetCreatorAuthority,
      global: GLOBAL_PDA,
      mint,
      quoteMint,
      quoteTokenProgram,
      associatedTokenProgram: import_spl_token3.ASSOCIATED_TOKEN_PROGRAM_ID,
      systemProgram: import_web33.SystemProgram.programId,
      bondingCurve: bondingCurvePda(mint),
      currentCreator,
      currentCreatorQuoteTokenAccount: ata(currentCreator),
      creatorVault,
      creatorVaultQuoteTokenAccount: ata(creatorVault),
      holderCreatorVault,
      holderCreatorVaultQuoteTokenAccount: ata(holderCreatorVault),
      pumpAmm: PUMP_AMM_PROGRAM_ID,
      ammGlobalConfig: AMM_GLOBAL_PDA,
      poolAuthority: pumpPoolAuthorityPda(mint),
      pool: canonicalPumpPoolPdaWithQuote(mint, quoteMint),
      pumpAmmEventAuthority: PUMP_AMM_EVENT_AUTHORITY_PDA,
      coinCreatorVaultAuthority,
      coinCreatorVaultAta: ata(coinCreatorVaultAuthority),
      sharingConfig: feeSharingConfigPda(mint),
      pumpFees: PUMP_FEE_PROGRAM_ID,
      pumpFeesEventAuthority: PUMP_FEE_EVENT_AUTHORITY_PDA,
      eventAuthority: PUMP_EVENT_AUTHORITY_PDA,
      program: PUMP_PROGRAM_ID
    }).instruction();
    if (!currentCreator.equals(import_web33.PublicKey.default)) {
      for (const key of instruction.keys) {
        if (key.pubkey.equals(currentCreator)) {
          key.isWritable = true;
        }
      }
    }
    return instruction;
  }
  /**
   * `distribute_fee_to_holders`: pays the fees collected on a holder-reward
   * coin's `holderRewardsPda(mint)` out to holders. Signed by
   * `Global.holderRewardClaimAuthority`, who also pays the rent of any
   * recipient quote ATA created (token quotes only). `recipients[i].amount`
   * goes to `recipients[i].owner`: as lamports on a SOL quote, as tokens into
   * the owner's quote ATA (created if missing) on a token quote. The program
   * checks `amounts.length * 2 == remaining accounts` and each ATA (6085),
   * refuses to leave the PDA between zero and its rent-exempt minimum on a
   * SOL quote (6086; draining it fully is fine) and needs
   * `holderRewardsTokenAccount` on a token quote (6087).
   *
   * The fees reach the PDA through the permissionless collects with the PDA
   * as `creator`: `collect_creator_fee` / `collect_creator_fee_v2` on the
   * curve and, after graduation, pump-amm's `collect_coin_creator_fee` or
   * `transfer_creator_fees_to_pump`.
   *
   * @param params.holderRewardsTokenAccount - Any quote token account owned
   *   by the PDA, normally `quoteAta(holderRewardsPda(mint), quoteMint,
   *   quoteTokenProgram)`. The payout source on a token quote; on a SOL quote
   *   a parked WSOL account that is closed into the PDA first. Omit when
   *   there is none (SOL quote only).
   */
  async distributeFeeToHoldersInstruction({
    holderRewardClaimAuthority,
    mint,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    recipients,
    holderRewardsTokenAccount
  }) {
    const isNative = quoteMint.equals(import_spl_token3.NATIVE_MINT);
    const remainingAccounts = recipients.flatMap(({ owner }) => [
      // Lamports land on the owner; a token payout only reads it as the ATA's authority.
      { pubkey: owner, isSigner: false, isWritable: isNative },
      {
        pubkey: quoteAta(owner, quoteMint, quoteTokenProgram),
        isSigner: false,
        isWritable: !isNative
      }
    ]);
    return await this.offlinePumpProgram.methods.distributeFeeToHolders(recipients.map(({ amount }) => amount)).accountsPartial({
      global: GLOBAL_PDA,
      holderRewardClaimAuthority,
      mint,
      holderRewards: holderRewardsPda(mint),
      holderRewardsTokenAccount: holderRewardsTokenAccount ?? null,
      quoteMint,
      quoteTokenProgram,
      associatedTokenProgram: import_spl_token3.ASSOCIATED_TOKEN_PROGRAM_ID,
      systemProgram: import_web33.SystemProgram.programId,
      eventAuthority: PUMP_EVENT_AUTHORITY_PDA,
      program: PUMP_PROGRAM_ID
    }).remainingAccounts(remainingAccounts).instruction();
  }
  /**
   * pump-fees `set_exotic_flat_fees` on the pump `FeeConfig`
   * (`PUMP_FEE_CONFIG_PDA`): the flat schedule canonical curves and pools pay
   * when quoted in a mint that is neither SOL-like nor a listed stable (see
   * `selectCurveFeeSchedule`). `admin` signs, must be `FeeConfig.admin`, and
   * pays the rent top-up when the account still has the pre-exotic length.
   * All-zero fees mean unset: the program then charges `flatFees`.
   */
  async setExoticFlatFeesInstruction({
    admin,
    exoticFlatFees
  }) {
    return await this.offlinePumpFeeProgram.methods.setExoticFlatFees(exoticFlatFees).accountsPartial({ admin, configProgramId: PUMP_PROGRAM_ID }).instruction();
  }
  async getBuyInstructionRaw({
    user,
    mint,
    creator,
    amount,
    solAmount,
    feeRecipient = getStaticRandomFeeRecipient(),
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    buybackFeeRecipient = getStaticRandomFeeRecipientForBuyback()
  }) {
    return await this.getBuyInstructionInternal({
      user,
      associatedUser: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        user,
        true,
        tokenProgram
      ),
      mint,
      creator,
      feeRecipient,
      buybackFeeRecipient,
      amount,
      solAmount,
      tokenProgram
    });
  }
  async getBuyInstructionInternal({
    user,
    associatedUser,
    mint,
    creator,
    feeRecipient,
    buybackFeeRecipient,
    amount,
    solAmount,
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    return await this.offlinePumpProgram.methods.buy(amount, solAmount, { 0: true }).accountsPartial({
      feeRecipient,
      mint,
      associatedUser,
      user,
      creatorVault: creatorVaultPda(creator),
      tokenProgram
    }).remainingAccounts([
      {
        pubkey: bondingCurveV2Pda(mint),
        isWritable: false,
        isSigner: false
      },
      {
        pubkey: buybackFeeRecipient,
        isWritable: true,
        isSigner: false
      }
    ]).instruction();
  }
  async getSellInstructionRaw({
    user,
    mint,
    creator,
    amount,
    solAmount,
    feeRecipient = getStaticRandomFeeRecipient(),
    buybackFeeRecipient = getStaticRandomFeeRecipientForBuyback(),
    tokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    cashback = false
  }) {
    return await this.getSellInstructionInternal({
      user,
      mint,
      creator,
      feeRecipient,
      buybackFeeRecipient,
      amount,
      solAmount,
      tokenProgram,
      cashback
    });
  }
  async getSellInstructionInternal({
    user,
    mint,
    creator,
    feeRecipient,
    buybackFeeRecipient,
    amount,
    solAmount,
    tokenProgram,
    cashback
  }) {
    const userVolumeAccumulator = userVolumeAccumulatorPda(user);
    const fixedRemaininAccounts = [
      {
        pubkey: bondingCurveV2Pda(mint),
        isWritable: false,
        isSigner: false
      },
      {
        pubkey: buybackFeeRecipient,
        isWritable: true,
        isSigner: false
      }
    ];
    return await this.offlinePumpProgram.methods.sell(amount, solAmount).accountsPartial({
      feeRecipient,
      mint,
      associatedUser: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        user,
        true,
        tokenProgram
      ),
      user,
      creatorVault: creatorVaultPda(creator),
      tokenProgram
    }).remainingAccounts(
      cashback ? [
        {
          pubkey: userVolumeAccumulator,
          isWritable: true,
          isSigner: false
        },
        ...fixedRemaininAccounts
      ] : fixedRemaininAccounts
    ).instruction();
  }
  async buyV2Instructions({
    global,
    bondingCurveAccountInfo,
    bondingCurve,
    associatedUserAccountInfo,
    mint,
    user,
    amount,
    quoteAmount,
    slippage,
    tokenProgram = import_spl_token3.TOKEN_2022_PROGRAM_ID,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const instructions = [];
    const associatedUser = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      user,
      true,
      tokenProgram
    );
    if (!associatedUserAccountInfo) {
      instructions.push(
        (0, import_spl_token3.createAssociatedTokenAccountIdempotentInstruction)(
          user,
          associatedUser,
          user,
          mint,
          tokenProgram
        )
      );
    }
    const quoteMint = isLegacyQuoteMint(bondingCurve.quoteMint) ? import_spl_token3.NATIVE_MINT : bondingCurve.quoteMint;
    instructions.push(
      await this.buyV2Instruction({
        global,
        mint,
        creator: bondingCurve.creator,
        user,
        associatedUser,
        amount,
        quoteAmount,
        slippage,
        tokenProgram,
        quoteMint,
        quoteTokenProgram,
        mayhemMode: bondingCurve.isMayhemMode
      })
    );
    return instructions;
  }
  /**
   * `create_v2` + the user's base ATA + a first `buy_v2`, all agreeing on the
   * quote. See `createV2Instruction` for the quote rules and the compute
   * budget to add (~500k CU for a token quote).
   *
   * @param params.quoteTokenProgram - The program that owns `quoteMint`; used
   *   by both the create and the buy. Defaults to `TOKEN_PROGRAM_ID` (SOL,
   *   USDC); `OnlinePumpSdk.fetchQuoteTokenProgram` resolves it.
   * @param params.creatorFeeBps - Forwarded to `createV2Instruction`. Unlike
   *   that builder this one holds `global`, so a nonzero rate the program
   *   would reject throws up front: `CreatorFeeNotConfigurableError` (gate
   *   off), `CreatorFeeBpsOutOfRangeError` (outside
   *   `1..=global.maxConfigurableCreatorFeeBps`). Quote `amount` with the same
   *   rate (`getBuyTokenAmountFromSolAmount`'s `creatorFeeBps`), or the buy's
   *   `quoteAmount` falls short of the fees the program charges.
   * @param params.holderReward - Forwarded to `createV2Instruction`; the buy
   *   then targets the holder-rewards PDA's creator vault, as the program
   *   does. Throws `HolderRewardDisabledError` while
   *   `global.isHolderRewardEnabled` is off.
   * @param params.cashback - Deprecated: throws `CashbackDeprecatedError`
   *   when `true`, as `create_v2` would fail with 6082.
   */
  async createV2AndBuyV2Instructions({
    global,
    mint,
    name,
    symbol,
    uri,
    creator,
    user,
    amount,
    quoteAmount,
    mayhemMode,
    cashback = false,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    creatorFeeBps,
    holderReward = false
  }) {
    assertCreateV2FlagsAllowed({
      global,
      mint,
      cashback,
      holderReward,
      creatorFeeBps
    });
    const associatedUser = (0, import_spl_token3.getAssociatedTokenAddressSync)(
      mint,
      user,
      true,
      import_spl_token3.TOKEN_2022_PROGRAM_ID
    );
    const { buyQuoteMint, buyQuoteTokenProgram } = createAndBuyQuote(
      quoteMint,
      quoteTokenProgram
    );
    return [
      await this.createV2Instruction({
        mint,
        name,
        symbol,
        uri,
        creator,
        user,
        mayhemMode,
        cashback,
        quoteMint,
        quoteTokenProgram,
        creatorFeeBps,
        holderReward
      }),
      (0, import_spl_token3.createAssociatedTokenAccountIdempotentInstruction)(
        user,
        associatedUser,
        user,
        mint,
        import_spl_token3.TOKEN_2022_PROGRAM_ID
      ),
      await this.buyV2Instruction({
        global,
        mint,
        creator: createdCurveCreator(mint, creator, holderReward),
        user,
        associatedUser,
        amount,
        quoteAmount,
        slippage: 1,
        tokenProgram: import_spl_token3.TOKEN_2022_PROGRAM_ID,
        quoteMint: buyQuoteMint,
        quoteTokenProgram: buyQuoteTokenProgram,
        mayhemMode
      })
    ];
  }
  async buyV2Instruction({
    global,
    mint,
    creator,
    user,
    associatedUser,
    amount,
    quoteAmount,
    slippage,
    tokenProgram = import_spl_token3.TOKEN_2022_PROGRAM_ID,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID,
    mayhemMode = false
  }) {
    return await this.getBuyV2InstructionInternal({
      user,
      associatedUser,
      mint,
      creator,
      feeRecipient: getFeeRecipient(global, mayhemMode),
      buybackFeeRecipient: getStaticRandomFeeRecipientForBuyback(),
      amount,
      quoteAmount: quoteAmount.add(
        quoteAmount.mul(new import_bn4.default(Math.floor(slippage * 10))).div(new import_bn4.default(1e3))
      ),
      tokenProgram,
      quoteMint,
      quoteTokenProgram
    });
  }
  async sellV2Instructions({
    global,
    bondingCurveAccountInfo,
    bondingCurve,
    mint,
    user,
    amount,
    quoteAmount,
    slippage,
    tokenProgram = import_spl_token3.TOKEN_2022_PROGRAM_ID,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const instructions = [];
    const quoteMint = isLegacyQuoteMint(bondingCurve.quoteMint) ? import_spl_token3.NATIVE_MINT : bondingCurve.quoteMint;
    instructions.push(
      await this.getSellV2InstructionInternal({
        user,
        mint,
        creator: bondingCurve.creator,
        feeRecipient: getFeeRecipient(global, bondingCurve.isMayhemMode),
        buybackFeeRecipient: getStaticRandomFeeRecipientForBuyback(),
        amount,
        quoteAmount: quoteAmount.sub(
          quoteAmount.mul(new import_bn4.default(Math.floor(slippage * 10))).div(new import_bn4.default(1e3))
        ),
        tokenProgram,
        quoteMint,
        quoteTokenProgram
      })
    );
    return instructions;
  }
  async getBuyV2InstructionRaw({
    user,
    mint,
    creator,
    amount,
    quoteAmount,
    feeRecipient = getStaticRandomFeeRecipient(),
    buybackFeeRecipient = getStaticRandomFeeRecipientForBuyback(),
    tokenProgram = import_spl_token3.TOKEN_2022_PROGRAM_ID,
    quoteMint = import_spl_token3.NATIVE_MINT,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    return await this.getBuyV2InstructionInternal({
      user,
      associatedUser: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        user,
        true,
        tokenProgram
      ),
      mint,
      creator,
      feeRecipient,
      buybackFeeRecipient,
      amount,
      quoteAmount,
      tokenProgram,
      quoteMint,
      quoteTokenProgram
    });
  }
  async getBuyV2InstructionInternal({
    user,
    associatedUser,
    mint,
    creator,
    feeRecipient,
    buybackFeeRecipient,
    amount,
    quoteAmount,
    tokenProgram,
    quoteMint,
    quoteTokenProgram
  }) {
    const bondingCurve = bondingCurvePda(mint);
    const creatorVault = creatorVaultPda(creator);
    const userVolumeAccumulator = userVolumeAccumulatorPda(user);
    return await this.offlinePumpProgram.methods.buyV2(amount, quoteAmount).accountsPartial({
      baseMint: mint,
      quoteMint,
      baseTokenProgram: tokenProgram,
      quoteTokenProgram,
      feeRecipient,
      associatedQuoteFeeRecipient: quoteAta(
        feeRecipient,
        quoteMint,
        quoteTokenProgram
      ),
      buybackFeeRecipient,
      associatedQuoteBuybackFeeRecipient: quoteAta(
        buybackFeeRecipient,
        quoteMint,
        quoteTokenProgram
      ),
      associatedBaseBondingCurve: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        bondingCurve,
        true,
        tokenProgram
      ),
      associatedQuoteBondingCurve: quoteAta(
        bondingCurve,
        quoteMint,
        quoteTokenProgram
      ),
      user,
      associatedBaseUser: associatedUser,
      associatedQuoteUser: quoteAta(user, quoteMint, quoteTokenProgram),
      creatorVault,
      associatedCreatorVault: quoteAta(
        creatorVault,
        quoteMint,
        quoteTokenProgram
      ),
      associatedUserVolumeAccumulator: quoteAta(
        userVolumeAccumulator,
        quoteMint,
        quoteTokenProgram
      )
    }).instruction();
  }
  async getSellV2InstructionRaw({
    user,
    mint,
    creator,
    amount,
    quoteAmount,
    feeRecipient = getStaticRandomFeeRecipient(),
    buybackFeeRecipient = getStaticRandomFeeRecipientForBuyback(),
    tokenProgram = import_spl_token3.TOKEN_2022_PROGRAM_ID,
    quoteMint = import_spl_token3.NATIVE_MINT,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    return await this.getSellV2InstructionInternal({
      user,
      mint,
      creator,
      feeRecipient,
      buybackFeeRecipient,
      amount,
      quoteAmount,
      tokenProgram,
      quoteMint,
      quoteTokenProgram
    });
  }
  async getSellV2InstructionInternal({
    user,
    mint,
    creator,
    feeRecipient,
    buybackFeeRecipient,
    amount,
    quoteAmount,
    tokenProgram,
    quoteMint,
    quoteTokenProgram
  }) {
    const bondingCurve = bondingCurvePda(mint);
    const creatorVault = creatorVaultPda(creator);
    const userVolumeAccumulator = userVolumeAccumulatorPda(user);
    return await this.offlinePumpProgram.methods.sellV2(amount, quoteAmount).accountsPartial({
      baseMint: mint,
      quoteMint,
      baseTokenProgram: tokenProgram,
      quoteTokenProgram,
      feeRecipient,
      associatedQuoteFeeRecipient: quoteAta(
        feeRecipient,
        quoteMint,
        quoteTokenProgram
      ),
      buybackFeeRecipient,
      associatedQuoteBuybackFeeRecipient: quoteAta(
        buybackFeeRecipient,
        quoteMint,
        quoteTokenProgram
      ),
      associatedBaseBondingCurve: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        bondingCurve,
        true,
        tokenProgram
      ),
      associatedQuoteBondingCurve: quoteAta(
        bondingCurve,
        quoteMint,
        quoteTokenProgram
      ),
      user,
      associatedBaseUser: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        mint,
        user,
        true,
        tokenProgram
      ),
      associatedQuoteUser: quoteAta(user, quoteMint, quoteTokenProgram),
      creatorVault,
      associatedCreatorVault: quoteAta(
        creatorVault,
        quoteMint,
        quoteTokenProgram
      ),
      associatedUserVolumeAccumulator: quoteAta(
        userVolumeAccumulator,
        quoteMint,
        quoteTokenProgram
      )
    }).instruction();
  }
  /**
   * Creates a fee sharing configuration for a token.
   *
   * @param params - Parameters for creating a fee sharing configuration
   * @param params.creator - The creator of the token
   * @param params.mint - The mint address of the token
   * @param params.pool - The pool address of the token (null for ungraduated coins)
   */
  async createFeeSharingConfig({
    creator,
    mint,
    pool
  }) {
    return await this.offlinePumpFeeProgram.methods.createFeeSharingConfig().accountsPartial({
      payer: creator,
      mint,
      pool
    }).instruction();
  }
  /**
   * Updates the fee shares for a token's creator fee distribution.
   *
   * @param params - Parameters for updating fee shares
   * @param params.authority - The current authority that can modify the fee sharing config
   * @param params.mint - The mint address of the token
   * @param params.currentShareholders - Array of current shareholders
   * @param params.newShareholders - Array of new shareholders and their share percentages
   * @requirements for newShareholders:
   * - Must contain at least 1 shareholder (cannot be empty)
   * - Maximum of 10 shareholders allowed
   * - Each shareholder must have a positive share (shareBps > 0)
   * - Total shares must equal exactly 10,000 basis points (100%)
   * - No duplicate addresses allowed
   * - shareBps is in basis points where 1 bps = 0.01% (e.g., 1500 = 15%)
   * @throws {NoShareholdersError} If shareholders array is empty
   * @throws {TooManyShareholdersError} If more than 10 shareholders
   * @throws {ZeroShareError} If any shareholder has zero or negative shares
   * @throws {InvalidShareTotalError} If total shares don't equal 10,000 basis points
   * @throws {DuplicateShareholderError} If duplicate addresses are found
   * @example
   * ```typescript
   * const instruction = await PUMP_SDK.updateFeeShares({
   *   authority: authorityPublicKey,
   *   mint: mintPublicKey,
   *   curShareholders: [wallet1, wallet2, wallet3],
   *   newShareholders: [
   *     { address: wallet1, shareBps: 5000 }, // 50%
   *     { address: wallet2, shareBps: 3000 }, // 30%
   *     { address: wallet3, shareBps: 2000 }, // 20%
   *   ]
   * });
   * ```
   */
  async updateFeeShares({
    authority,
    mint,
    currentShareholders,
    newShareholders
  }) {
    if (newShareholders.length === 0) {
      throw new NoShareholdersError();
    }
    if (newShareholders.length > MAX_SHAREHOLDERS) {
      throw new TooManyShareholdersError(
        newShareholders.length,
        MAX_SHAREHOLDERS
      );
    }
    let totalShares = 0;
    const addresses = /* @__PURE__ */ new Set();
    for (const shareholder of newShareholders) {
      if (shareholder.shareBps <= 0) {
        throw new ZeroShareError(shareholder.address.toString());
      }
      totalShares += shareholder.shareBps;
      addresses.add(shareholder.address.toString());
    }
    if (totalShares !== 1e4) {
      throw new InvalidShareTotalError(totalShares);
    }
    if (addresses.size !== newShareholders.length) {
      throw new DuplicateShareholderError();
    }
    const sharingConfigPda = feeSharingConfigPda(mint);
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk2.coinCreatorVaultAuthorityPda)(sharingConfigPda);
    return await this.offlinePumpFeeProgram.methods.updateFeeShares(
      newShareholders.map((sh) => ({
        address: sh.address,
        shareBps: sh.shareBps
      }))
    ).accountsPartial({
      authority,
      mint,
      coinCreatorVaultAta: (0, import_pump_swap_sdk2.coinCreatorVaultAtaPda)(
        coinCreatorVaultAuthority,
        import_spl_token3.NATIVE_MINT,
        import_spl_token3.TOKEN_PROGRAM_ID
      )
    }).remainingAccounts(
      currentShareholders.map((pubkey) => ({
        pubkey,
        isWritable: true,
        isSigner: false
      }))
    ).instruction();
  }
  /**
   * Updates the fee shares for a token's creator fee distribution, for a coin
   * quoted in any mint. `updateFeeShares` (v1) only handles SOL-quoted coins;
   * a non-SOL coin must use this instruction so the pending fees it pays out
   * first move through the right quote ATAs.
   *
   * @param params - Parameters for updating fee shares
   * @param params.authority - The current authority that can modify the fee sharing config
   * @param params.mint - The mint address of the token
   * @param params.currentShareholders - Array of current shareholders
   * @param params.newShareholders - Array of new shareholders and their share percentages
   * @param params.quoteMint - The coin's quote mint (`NATIVE_MINT` for SOL
   *   coins)
   * @param params.quoteTokenProgram - The program that owns `quoteMint`; every
   *   quote ATA (the vault's and each shareholder's) is derived with it. The
   *   `TOKEN_PROGRAM_ID` default is only right for SOL and USDC; pass the
   *   mint's owner (`OnlinePumpSdk.fetchQuoteTokenProgram`) for anything else.
   * @requirements for newShareholders:
   * - Must contain at least 1 shareholder (cannot be empty)
   * - Maximum of 10 shareholders allowed
   * - Each shareholder must have a positive share (shareBps > 0)
   * - Total shares must equal exactly 10,000 basis points (100%)
   * - No duplicate addresses allowed
   * - shareBps is in basis points where 1 bps = 0.01% (e.g., 1500 = 15%)
   * @throws {NoShareholdersError} If shareholders array is empty
   * @throws {TooManyShareholdersError} If more than 10 shareholders
   * @throws {ZeroShareError} If any shareholder has zero or negative shares
   * @throws {InvalidShareTotalError} If total shares don't equal 10,000 basis points
   * @throws {DuplicateShareholderError} If duplicate addresses are found
   */
  async updateFeeSharesV2({
    authority,
    mint,
    currentShareholders,
    newShareholders,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    if (newShareholders.length === 0) {
      throw new NoShareholdersError();
    }
    if (newShareholders.length > MAX_SHAREHOLDERS) {
      throw new TooManyShareholdersError(
        newShareholders.length,
        MAX_SHAREHOLDERS
      );
    }
    let totalShares = 0;
    const addresses = /* @__PURE__ */ new Set();
    for (const shareholder of newShareholders) {
      if (shareholder.shareBps <= 0) {
        throw new ZeroShareError(shareholder.address.toString());
      }
      totalShares += shareholder.shareBps;
      addresses.add(shareholder.address.toString());
    }
    if (totalShares !== 1e4) {
      throw new InvalidShareTotalError(totalShares);
    }
    if (addresses.size !== newShareholders.length) {
      throw new DuplicateShareholderError();
    }
    const sharingConfigPda = feeSharingConfigPda(mint);
    const coinCreatorVaultAuthority = (0, import_pump_swap_sdk2.coinCreatorVaultAuthorityPda)(sharingConfigPda);
    const remainingAccounts = [
      ...currentShareholders.map((pubkey) => ({
        pubkey,
        isWritable: true,
        isSigner: false
      })),
      ...quoteMint.equals(import_spl_token3.NATIVE_MINT) ? [] : currentShareholders.map((pubkey) => ({
        pubkey: (0, import_spl_token3.getAssociatedTokenAddressSync)(
          quoteMint,
          pubkey,
          true,
          quoteTokenProgram
        ),
        isWritable: true,
        isSigner: false
      }))
    ];
    return await this.offlinePumpFeeProgram.methods.updateFeeSharesV2(
      newShareholders.map((sh) => ({
        address: sh.address,
        shareBps: sh.shareBps
      }))
    ).accountsPartial({
      authority,
      mint,
      coinCreatorVaultAta: (0, import_pump_swap_sdk2.coinCreatorVaultAtaPda)(
        coinCreatorVaultAuthority,
        quoteMint,
        quoteTokenProgram
      ),
      quoteMint,
      tokenProgram: quoteTokenProgram,
      associatedTokenProgram: import_spl_token3.ASSOCIATED_TOKEN_PROGRAM_ID,
      systemProgram: import_web33.SystemProgram.programId
    }).remainingAccounts([...remainingAccounts]).instruction();
  }
  /**
   * Sweeps coin creator fees that have accrued on the Pump AMM into the
   * bonding curve creator vault, so they can later be paid out via
   * `distributeCreatorFeesV2`. Permissionless.
   *
   * For wrapped-SOL quotes the instruction closes & recreates the AMM coin
   * creator vault ATA and forwards the unwrapped lamports to `pump_creator_vault`.
   * For non-native quotes it does a token transfer between ATAs and creates
   * the destination `pump_creator_vault_ata` on the fly if it does not exist
   * (rent paid by `payer`).
   *
   * Assumes the coin has been opted into fee sharing (i.e. `coin_creator` on
   * the AMM pool is the `sharing_config` PDA for `mint`).
   *
   * @param params - Parameters for the transfer
   * @param params.payer - Transaction signer. Pays the rent for `pump_creator_vault_ata` when it has to be initialized (non-WSOL quotes only).
   * @param params.mint - The mint address of the token. Used to derive the sharing_config PDA, which is the coin creator post-migration.
   * @param params.quoteMint - The quote mint of the coin (use `NATIVE_MINT` for SOL-paired coins).
   * @param params.quoteTokenProgram - The program that owns `quoteMint`; both
   *   vault ATAs are derived with it. The `TOKEN_PROGRAM_ID` default is only
   *   right for SOL and USDC; pass the mint's owner
   *   (`OnlinePumpSdk.fetchQuoteTokenProgram`) for a Token-2022 quote.
   */
  async transferCreatorFeesToPumpV2({
    payer,
    mint,
    quoteMint,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const sharingConfigPda = feeSharingConfigPda(mint);
    return await this.offlinePumpAmmProgram.methods.transferCreatorFeesToPumpV2().accountsPartial({
      payer,
      quoteMint,
      tokenProgram: quoteTokenProgram,
      coinCreator: sharingConfigPda
    }).instruction();
  }
  decodeDistributeCreatorFeesEvent(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "distributeCreatorFeesEvent",
      data
    );
  }
  async distributeCreatorFees({
    mint,
    sharingConfig,
    sharingConfigAddress
  }) {
    return await this.offlinePumpProgram.methods.distributeCreatorFees().accountsPartial({
      mint,
      creatorVault: creatorVaultPda(sharingConfigAddress)
    }).remainingAccounts(
      sharingConfig.shareholders.map((shareholder) => ({
        pubkey: shareholder.address,
        isWritable: true,
        isSigner: false
      }))
    ).instruction();
  }
  /**
   * Distributes a coin's accrued creator fees to its sharing-config
   * shareholders, for a coin quoted in any mint (`distributeCreatorFees` is
   * SOL-only). For a non-SOL quote the program pays each shareholder's ATA
   * and, with `shouldInitializeAta`, creates missing ones at `payer`'s cost.
   *
   * @param params.quoteMint - The coin's quote mint (`NATIVE_MINT` for SOL
   *   coins).
   * @param params.quoteTokenProgram - The program that owns `quoteMint`; the
   *   vault's and every shareholder's quote ATA is derived with it. The
   *   `TOKEN_PROGRAM_ID` default is only right for SOL and USDC; pass the
   *   mint's owner (`OnlinePumpSdk.fetchQuoteTokenProgram`) for anything else.
   */
  async distributeCreatorFeesV2({
    mint,
    sharingConfig,
    sharingConfigAddress,
    quoteMint,
    payer,
    shouldInitializeAta = true,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const remainingAccounts = sharingConfig.shareholders.map((shareholder) => ({
      pubkey: shareholder.address,
      isWritable: true,
      isSigner: false
    }));
    if (!quoteMint.equals(import_spl_token3.NATIVE_MINT)) {
      remainingAccounts.push(
        ...sharingConfig.shareholders.map((shareholder) => ({
          pubkey: (0, import_spl_token3.getAssociatedTokenAddressSync)(
            quoteMint,
            shareholder.address,
            true,
            quoteTokenProgram
          ),
          isWritable: true,
          isSigner: false
        }))
      );
    }
    return await this.offlinePumpProgram.methods.distributeCreatorFeesV2(shouldInitializeAta).accountsPartial({
      mint,
      creatorVault: creatorVaultPda(sharingConfigAddress),
      quoteMint,
      quoteTokenProgram,
      associatedTokenProgram: import_spl_token3.ASSOCIATED_TOKEN_PROGRAM_ID,
      systemProgram: import_web33.SystemProgram.programId,
      payer
    }).remainingAccounts([...remainingAccounts]).instruction();
  }
  decodeMinimumDistributableFee(data) {
    return this.offlinePumpProgram.coder.types.decode(
      "minimumDistributableFeeEvent",
      data
    );
  }
  async getMinimumDistributableFee({
    mint,
    sharingConfig,
    sharingConfigAddress
  }) {
    return await this.offlinePumpProgram.methods.getMinimumDistributableFee().accountsPartial({
      mint,
      creatorVault: creatorVaultPda(sharingConfigAddress)
    }).remainingAccounts(
      sharingConfig.shareholders.map((shareholder) => ({
        pubkey: shareholder.address,
        isWritable: true,
        isSigner: false
      }))
    ).instruction();
  }
  /**
   * Creates a `DonationFeePda` for a `(mint, configId)` pair under the
   * pump-fees program. This PDA is the on-chain fee destination used when
   * routing a slice of creator fees to a donate.gg config; once created, you
   * can pass `donationFeePda(mint)` as a shareholder address in a
   * subsequent `updateFeeShares` call.
   *
   * The instruction is idempotent.
   *
   * @param params - Parameters for creating the donation fee PDA
   * @param params.coinCreator - The coin creator wallet; signs and pays rent
   *   for the new PDA. This is either the bonding curve's `creator`
   *   or the canonical pump-amm pool's `coin_creator`
   *   or the sharing_config.admin.
   * @param params.mint - Base mint of the coin whose creator fees are routed.
   * @param params.configId - The donate.gg config id this PDA escrows for.
   * @param params.quoteMint - The quote mint of the coin. You can pass
   *   `bondingCurve.quoteMint` directly: it is normalized via
   *   `normalizeQuoteMint`, so `PublicKey.default` (stored by legacy SOL
   *   coins) and `undefined` both resolve to `NATIVE_MINT`. Required for
   *   graduated non-SOL-quote coins: the canonical pool PDA is seeded by
   *   quote mint, so passing the wrong quote derives a nonexistent pool and
   *   the program rejects with `InvalidPool`. Ignored by the program for
   *   ungraduated coins.
   */
  async createDonationFeePda({
    coinCreator,
    mint,
    configId,
    quoteMint
  }) {
    return await this.offlinePumpFeeProgram.methods.createDonationFeePda().accountsPartial({
      payer: coinCreator,
      configId,
      baseMint: mint,
      pool: canonicalPumpPoolPdaWithQuote(
        mint,
        normalizeQuoteMint(quoteMint)
      ),
      donationFeePda: donationFeePda(mint, configId)
    }).instruction();
  }
  /**
   * Cranks a previously-created `DonationFeePda`, forwarding its full
   * `donationFeePdaAta` balance into the donation relay program's debouncer
   * for the relayer to settle later.
   *
   * The instruction is **permissionless** — anyone can call it, paying the
   * tx fee (and rent for the WSOL ATA on first crank). The pump-fees handler
   * also wraps any bare lamports sitting on the `DonationFeePda` into its
   * WSOL ATA before forwarding (native quote path), so the only state needed
   * to crank is the `(mint, configId)` pair (the `configId` is read back from
   * the PDA by the relay CPI, but the caller still needs it to derive the
   * relay-side epoch_tracker / debouncer PDAs).
   *
   * Quote mint defaults to wrapped SOL (`NATIVE_MINT`). If/when other quote
   * mints are supported, override `quoteMint` to match the value stored on
   * the on-chain `DonationFeePda.quote_mint` (the program enforces equality
   * and will error otherwise).
   *
   * @param params - Parameters for cranking the donation fee PDA
   * @param params.payer - Wallet that signs and pays for `init_if_needed` ATAs.
   * @param params.mint - Base mint of the coin (the one whose creator fees
   *   feed the PDA — matches `DonationFeePda.base_mint`).
   * @param params.configId - The 32-byte donate.gg config id bound to the
   *   PDA; used to derive the relay's epoch tracker and debouncer PDAs.
   * @param params.donationRelayProgramId - Program id of the Donation Relay
   *   program for the target cluster (e.g. `DONATION_RELAY_PROGRAM_ID_MAINNET`
   *   or `DONATION_RELAY_PROGRAM_ID_DEVNET`).
   * @param params.quoteMint - Quote mint that the relay debounces in. Defaults
   *   to `NATIVE_MINT` (WSOL). Must equal `DonationFeePda.quote_mint`.
   */
  async crankDonationFeePda({
    payer,
    mint,
    configId,
    donationRelayProgramId,
    quoteMint = import_spl_token3.NATIVE_MINT
  }) {
    const donationFeePdaAddress = donationFeePda(mint, configId);
    const epochTracker = donationRelayEpochTrackerPda(
      configId,
      quoteMint,
      donationRelayProgramId
    );
    const debouncer = donationRelayDebouncerPda(
      configId,
      quoteMint,
      donationRelayProgramId
    );
    return await this.offlinePumpFeeProgram.methods.crankDonationFeePda().accountsPartial({
      payer,
      donationFeePda: donationFeePdaAddress,
      quoteMint,
      donationFeePdaAta: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        quoteMint,
        donationFeePdaAddress,
        true,
        import_spl_token3.TOKEN_PROGRAM_ID
      ),
      donationRelayProgram: donationRelayProgramId,
      donationRelayEventAuthority: donationRelayEventAuthorityPda(
        donationRelayProgramId
      ),
      mintWhitelist: donationRelayMintWhitelistPda(donationRelayProgramId),
      epochTracker,
      debouncer,
      debouncerAta: (0, import_spl_token3.getAssociatedTokenAddressSync)(
        quoteMint,
        debouncer,
        true,
        import_spl_token3.TOKEN_PROGRAM_ID
      )
    }).instruction();
  }
  /**
   * Creates a social fee PDA that can accumulate fees for a social media user.
   *
   * @param params - Parameters for creating the social fee PDA
   * @param params.payer - The account paying for the transaction
   * @param params.userId - The user ID string (max 20 characters, typically the numeric social media user ID)
   * @param params.platform - Platform identifier (0=pump, 1=X, etc.)
   */
  async createSocialFeePda({
    payer,
    userId,
    platform
  }) {
    return await this.offlinePumpFeeProgram.methods.createSocialFeePda(userId, platform).accountsPartial({
      payer,
      socialFeePda: socialFeePda(userId, platform)
    }).instruction();
  }
  // Internal use only
  async claimSocialFeePda({
    recipient,
    socialClaimAuthority,
    userId,
    platform
  }) {
    return await this.offlinePumpFeeProgram.methods.claimSocialFeePda(userId, platform).accountsPartial({
      recipient,
      socialFeePda: socialFeePda(userId, platform),
      socialClaimAuthority
    }).instruction();
  }
  async claimCashbackInstruction({
    user
  }) {
    return await this.offlinePumpProgram.methods.claimCashback().accountsPartial({
      user
    }).instruction();
  }
  /**
   * `claim_cashback_v2`: pays out the cashback a user accrued in `quoteMint`
   * from their volume accumulator's quote ATA to their own quote ATA.
   *
   * @param params.quoteMint - The quote the cashback accrued in; defaults to
   *   `NATIVE_MINT` (SOL).
   * @param params.quoteTokenProgram - The program that owns `quoteMint`; both
   *   ATAs are derived with it. The `TOKEN_PROGRAM_ID` default is only right
   *   for SOL and USDC; pass the mint's owner
   *   (`OnlinePumpSdk.fetchQuoteTokenProgram`) for a Token-2022 quote.
   */
  async claimCashbackV2Instruction({
    user,
    quoteMint = import_spl_token3.NATIVE_MINT,
    quoteTokenProgram = import_spl_token3.TOKEN_PROGRAM_ID
  }) {
    const userVolumeAccumulator = userVolumeAccumulatorPda(user);
    return await this.offlinePumpProgram.methods.claimCashbackV2().accountsPartial({
      user,
      quoteMint,
      quoteTokenProgram,
      associatedUserVolumeAccumulator: quoteAta(
        userVolumeAccumulator,
        quoteMint,
        quoteTokenProgram
      ),
      associatedQuoteUser: quoteAta(user, quoteMint, quoteTokenProgram)
    }).instruction();
  }
};
var PUMP_SDK = new PumpSdk();
function hasCoinCreatorMigratedToSharingConfig({
  mint,
  creator
}) {
  return feeSharingConfigPda(mint).equals(creator);
}
function isSharingConfigEditable({
  sharingConfig
}) {
  if (sharingConfig.version === 1) {
    return false;
  }
  if (sharingConfig.version === 2 && sharingConfig.adminRevoked) {
    return false;
  }
  return true;
}

// src/pda.ts
var GLOBAL_PDA = (0, import_pump_swap_sdk3.pumpPda)([import_buffer.Buffer.from("global")]);
var QUOTE_CONTROL_PDA = (0, import_pump_swap_sdk3.pumpPda)([import_buffer.Buffer.from("quote-control")]);
var AMM_GLOBAL_PDA = (0, import_pump_swap_sdk3.pumpAmmPda)([import_buffer.Buffer.from("amm_global")]);
var FEE_PROGRAM_GLOBAL_PDA = (0, import_pump_swap_sdk3.pumpFeePda)([
  import_buffer.Buffer.from("fee-program-global")
]);
var PUMP_FEE_CONFIG_PDA = (0, import_pump_swap_sdk3.pumpFeePda)([
  import_buffer.Buffer.from("fee_config"),
  PUMP_PROGRAM_ID.toBuffer()
]);
var GLOBAL_VOLUME_ACCUMULATOR_PDA = (0, import_pump_swap_sdk3.pumpPda)([
  import_buffer.Buffer.from("global_volume_accumulator")
]);
var AMM_GLOBAL_VOLUME_ACCUMULATOR_PDA = (0, import_pump_swap_sdk3.pumpAmmPda)([
  import_buffer.Buffer.from("global_volume_accumulator")
]);
var PUMP_EVENT_AUTHORITY_PDA = getEventAuthorityPda(PUMP_PROGRAM_ID);
var PUMP_AMM_EVENT_AUTHORITY_PDA = getEventAuthorityPda(PUMP_AMM_PROGRAM_ID);
var PUMP_FEE_EVENT_AUTHORITY_PDA = getEventAuthorityPda(PUMP_FEE_PROGRAM_ID);
function getEventAuthorityPda(programId) {
  return import_web34.PublicKey.findProgramAddressSync(
    [import_buffer.Buffer.from("__event_authority")],
    programId
  )[0];
}
function bondingCurvePda(mint) {
  return (0, import_pump_swap_sdk3.pumpPda)([
    import_buffer.Buffer.from("bonding-curve"),
    new import_web34.PublicKey(mint).toBuffer()
  ]);
}
function bondingCurveV2Pda(mint) {
  return (0, import_pump_swap_sdk3.pumpPda)([
    import_buffer.Buffer.from("bonding-curve-v2"),
    new import_web34.PublicKey(mint).toBuffer()
  ]);
}
function creatorVaultPda(creator) {
  return (0, import_pump_swap_sdk3.pumpPda)([import_buffer.Buffer.from("creator-vault"), creator.toBuffer()]);
}
function holderRewardsPda(mint) {
  return (0, import_pump_swap_sdk3.pumpPda)([import_buffer.Buffer.from("holder-rewards"), mint.toBuffer()]);
}
function pumpPoolAuthorityPda(mint) {
  return (0, import_pump_swap_sdk3.pumpPda)([import_buffer.Buffer.from("pool-authority"), mint.toBuffer()]);
}
var CANONICAL_POOL_INDEX = 0;
function canonicalPumpPoolPda(mint) {
  return (0, import_pump_swap_sdk3.poolPda)(
    CANONICAL_POOL_INDEX,
    pumpPoolAuthorityPda(mint),
    mint,
    import_spl_token4.NATIVE_MINT
  );
}
function canonicalPumpPoolPdaWithQuote(mint, quoteMint) {
  return (0, import_pump_swap_sdk3.poolPda)(
    CANONICAL_POOL_INDEX,
    pumpPoolAuthorityPda(mint),
    mint,
    quoteMint
  );
}
function boostVaultAuthorityPda(pool) {
  return (0, import_pump_swap_sdk3.pumpAmmPda)([import_buffer.Buffer.from("boost_vault"), pool.toBuffer()]);
}
function userVolumeAccumulatorPda(user, program = PUMP_PROGRAM_ID) {
  if (program.equals(PUMP_PROGRAM_ID)) {
    return (0, import_pump_swap_sdk3.pumpPda)([import_buffer.Buffer.from("user_volume_accumulator"), user.toBuffer()]);
  }
  return (0, import_pump_swap_sdk3.pumpAmmPda)([import_buffer.Buffer.from("user_volume_accumulator"), user.toBuffer()]);
}
var getGlobalParamsPda = () => {
  return import_web34.PublicKey.findProgramAddressSync(
    [import_buffer.Buffer.from("global-params")],
    MAYHEM_PROGRAM_ID
  )[0];
};
var getMayhemStatePda = (mint) => {
  return import_web34.PublicKey.findProgramAddressSync(
    [import_buffer.Buffer.from("mayhem-state"), mint.toBuffer()],
    MAYHEM_PROGRAM_ID
  )[0];
};
var getSolVaultPda = () => {
  return import_web34.PublicKey.findProgramAddressSync(
    [import_buffer.Buffer.from("sol-vault")],
    MAYHEM_PROGRAM_ID
  )[0];
};
var getTokenVaultPda = (mintPubkey) => {
  return (0, import_spl_token4.getAssociatedTokenAddressSync)(
    mintPubkey,
    getSolVaultPda(),
    true,
    import_spl_token4.TOKEN_2022_PROGRAM_ID
  );
};
var feeSharingConfigPda = (mint) => {
  return (0, import_pump_swap_sdk3.pumpFeePda)([import_buffer.Buffer.from("sharing-config"), mint.toBuffer()]);
};
var isLegacyQuoteMint = (quoteMint) => quoteMint.equals(import_spl_token4.NATIVE_MINT) || quoteMint.equals(import_web34.PublicKey.default);
var normalizeQuoteMint = (quoteMint) => !quoteMint || isLegacyQuoteMint(quoteMint) ? import_spl_token4.NATIVE_MINT : quoteMint;
var quoteAta = (owner, quoteMint, quoteTokenProgram) => (0, import_spl_token4.getAssociatedTokenAddressSync)(quoteMint, owner, true, quoteTokenProgram);
var ammCreatorVaultPda = (creator) => {
  return import_web34.PublicKey.findProgramAddressSync(
    [import_buffer.Buffer.from("creator_vault"), creator.toBuffer()],
    PUMP_AMM_PROGRAM_ID
  )[0];
};
var socialFeePda = (userId, platform) => {
  return (0, import_pump_swap_sdk3.pumpFeePda)([
    import_buffer.Buffer.from("social-fee-pda"),
    import_buffer.Buffer.from(userId),
    import_buffer.Buffer.from([platform])
  ]);
};
var donationFeePda = (mint, configId) => {
  return (0, import_pump_swap_sdk3.pumpFeePda)([
    import_buffer.Buffer.from("donation-fee-pda"),
    mint.toBuffer(),
    configId.toBuffer()
  ]);
};
var DONATION_RELAY_PROGRAM_ID_MAINNET = new import_web34.PublicKey(
  "RLAYHr9TRFcKB2ubYQhspcnXiaGpaVzNQvHytt47RZu"
);
var DONATION_RELAY_PROGRAM_ID_DEVNET = new import_web34.PublicKey(
  "DRLYxueWz6iymdsaRCER6iv6v9zL7gFWANwDL2V5VUx1"
);
var donationRelayPda = (seeds, donationRelayProgramId) => {
  return import_web34.PublicKey.findProgramAddressSync(seeds, donationRelayProgramId)[0];
};
var donationRelayEpochTrackerPda = (configId, quoteMint, donationRelayProgramId) => {
  return donationRelayPda(
    [
      import_buffer.Buffer.from("epoch_tracker_v1"),
      configId.toBuffer(),
      quoteMint.toBuffer()
    ],
    donationRelayProgramId
  );
};
var donationRelayDebouncerPda = (configId, quoteMint, donationRelayProgramId) => {
  return donationRelayPda(
    [import_buffer.Buffer.from("debouncer_v1"), configId.toBuffer(), quoteMint.toBuffer()],
    donationRelayProgramId
  );
};
var donationRelayMintWhitelistPda = (donationRelayProgramId) => {
  return donationRelayPda(
    [import_buffer.Buffer.from("mint_whitelist_v1")],
    donationRelayProgramId
  );
};
var donationRelayEventAuthorityPda = (donationRelayProgramId) => {
  return getEventAuthorityPda(donationRelayProgramId);
};

// src/bondingCurve.ts
function initialVirtualQuoteReservesFor(global, quoteMint, quoteControl) {
  if (isLegacyQuoteMint(quoteMint)) {
    return global.initialVirtualSolReserves;
  }
  if (quoteMint.equals(import_spl_token5.NATIVE_MINT_2022)) {
    throw new UnsupportedQuoteMintError(quoteMint);
  }
  if (global.whitelistedQuoteMints.some((mint) => mint.equals(quoteMint))) {
    return global.initialVirtualQuoteReserves;
  }
  const entry = quoteControl?.mints.find(
    (candidate) => candidate.mint.equals(quoteMint)
  );
  if (entry) {
    return entry.initialVirtualQuoteReserves;
  }
  if (quoteControl !== void 0) {
    throw new UnsupportedQuoteMintError(quoteMint);
  }
  return global.initialVirtualQuoteReserves;
}
function newBondingCurve(global, quoteMint = import_web35.PublicKey.default, quoteControl, creatorFeeBps, isHolderReward = false) {
  const quote = quoteMint ?? import_web35.PublicKey.default;
  return {
    virtualTokenReserves: global.initialVirtualTokenReserves,
    virtualQuoteReserves: initialVirtualQuoteReservesFor(
      global,
      quote,
      quoteControl
    ),
    realTokenReserves: global.initialRealTokenReserves,
    realQuoteReserves: new import_bn5.default(0),
    tokenTotalSupply: global.tokenTotalSupply,
    complete: false,
    creator: import_web35.PublicKey.default,
    isMayhemMode: global.mayhemModeEnabled,
    isCashbackCoin: false,
    // Stored the way the program stores it: the zero key for SOL curves.
    quoteMint: isLegacyQuoteMint(quote) ? import_web35.PublicKey.default : quote,
    creatorFeeBps: creatorFeeBps ?? new import_bn5.default(0),
    canEditCreatorFee: false,
    isHolderReward
  };
}
function getBuySolAmountFromTokenAmountQuote({
  minAmount,
  virtualTokenReserves,
  virtualQuoteReserves
}) {
  return minAmount.mul(virtualQuoteReserves).div(virtualTokenReserves.sub(minAmount)).add(new import_bn5.default(1));
}
function getBuyTokenAmountFromSolAmountQuote({
  inputAmount,
  virtualTokenReserves,
  virtualQuoteReserves
}) {
  return inputAmount.mul(virtualTokenReserves).div(virtualQuoteReserves.add(inputAmount));
}
function getSellSolAmountFromTokenAmountQuote({
  inputAmount,
  virtualTokenReserves,
  virtualQuoteReserves
}) {
  return inputAmount.mul(virtualQuoteReserves).div(virtualTokenReserves.add(inputAmount));
}
function getBuyTokenAmountFromSolAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  quoteMint,
  quoteControl,
  creatorFeeBps
}) {
  if (amount.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  let isNewBondingCurve = false;
  if (bondingCurve === null || mintSupply === null) {
    bondingCurve = newBondingCurve(
      global,
      quoteMint,
      quoteControl,
      creatorFeeBps
    );
    mintSupply = global.tokenTotalSupply;
    isNewBondingCurve = true;
  }
  if (bondingCurve.virtualTokenReserves.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  const { virtualQuoteReserves, virtualTokenReserves } = bondingCurve;
  const { protocolFeeBps, creatorFeeBps: chargedCreatorFeeBps } = computeFeesBps({
    global,
    feeConfig,
    mintSupply,
    virtualQuoteReserves,
    virtualTokenReserves,
    quoteMint: bondingCurve.quoteMint,
    creatorFeeBps: bondingCurve.creatorFeeBps
  });
  const totalFeeBasisPoints = protocolFeeBps.add(
    isNewBondingCurve || !import_web35.PublicKey.default.equals(bondingCurve.creator) ? chargedCreatorFeeBps : new import_bn5.default(0)
  );
  const inputAmount = amount.subn(1).muln(1e4).div(totalFeeBasisPoints.addn(1e4));
  const tokensReceived = getBuyTokenAmountFromSolAmountQuote({
    inputAmount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves
  });
  return import_bn5.default.min(tokensReceived, bondingCurve.realTokenReserves);
}
function getBuySolAmountFromTokenAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount,
  quoteMint,
  quoteControl,
  creatorFeeBps
}) {
  if (amount.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  let isNewBondingCurve = false;
  if (bondingCurve === null || mintSupply === null) {
    bondingCurve = newBondingCurve(
      global,
      quoteMint,
      quoteControl,
      creatorFeeBps
    );
    mintSupply = global.tokenTotalSupply;
    isNewBondingCurve = true;
  }
  if (bondingCurve.virtualTokenReserves.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  const minAmount = import_bn5.default.min(amount, bondingCurve.realTokenReserves);
  const solCost = getBuySolAmountFromTokenAmountQuote({
    minAmount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves
  });
  return solCost.add(
    getFee({
      global,
      feeConfig,
      mintSupply,
      bondingCurve,
      amount: solCost,
      isNewBondingCurve
    })
  );
}
function getSellSolAmountFromTokenAmount({
  global,
  feeConfig,
  mintSupply,
  bondingCurve,
  amount
}) {
  if (amount.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  if (bondingCurve.virtualTokenReserves.eq(new import_bn5.default(0))) {
    return new import_bn5.default(0);
  }
  const solCost = getSellSolAmountFromTokenAmountQuote({
    inputAmount: amount,
    virtualTokenReserves: bondingCurve.virtualTokenReserves,
    virtualQuoteReserves: bondingCurve.virtualQuoteReserves
  });
  return solCost.sub(
    getFee({
      global,
      feeConfig,
      mintSupply,
      bondingCurve,
      amount: solCost,
      isNewBondingCurve: false
    })
  );
}
function getStaticRandomFeeRecipient() {
  const randomIndex = Math.floor(Math.random() * CURRENT_FEE_RECIPIENTS.length);
  return new import_web35.PublicKey(CURRENT_FEE_RECIPIENTS[randomIndex]);
}
var CURRENT_FEE_RECIPIENTS = [
  "62qc2CNXwrYqQScmEdiZFFAnJR262PxWEuNQtxfafNgV",
  "7VtfL8fvgNfhz17qKRMjzQEXgbdpnHHHQRh54R9jP2RJ",
  "7hTckgnGnLQR6sdH7YkqFTAA7VwTfYFaZ6EhEsU3saCX",
  "9rPYyANsfQZw3DnDmKE3YCQF5E8oD89UXoHn9JFEhJUz",
  "AVmoTthdrX6tKt4nDjco2D775W2YK3sDhxPcMmzUAmTY",
  "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM",
  "FWsW1xNtWscwNmKv6wVsU1iTzRN6wmmk3MjxRP5tT7hz",
  "G5UZAVbAf46s7cKWoyKu8kYTip9DGTpbLZ2qa9Aq69dP"
];
function getStaticRandomFeeRecipientForBuyback() {
  const randomIndex = Math.floor(
    Math.random() * CURRENT_FEE_RECIPIENTS_FOR_BUYBACK.length
  );
  return new import_web35.PublicKey(CURRENT_FEE_RECIPIENTS_FOR_BUYBACK[randomIndex]);
}
var CURRENT_FEE_RECIPIENTS_FOR_BUYBACK = [
  "5YxQFdt3Tr9zJLvkFccqXVUwhdTWJQc1fFg2YPbxvxeD",
  "9M4giFFMxmFGXtc3feFzRai56WbBqehoSeRE5GK7gf7",
  "GXPFM2caqTtQYC2cJ5yJRi9VDkpsYZXzYdwYpGnLmtDL",
  "3BpXnfJaUTiwXnJNe7Ej1rcbzqTTQUvLShZaWazebsVR",
  "5cjcW9wExnJJiqgLjq7DEG75Pm6JBgE1hNv4B2vHXUW6",
  "EHAAiTxcdDwQ3U4bU6YcMsQGaekdzLS3B5SmYo46kJtL",
  "5eHhjP8JaYkz83CWwvGU2uMUXefd3AazWGx4gpcuEEYD",
  "A7hAgCzFw14fejgCp387JUJRMNyz4j89JKnhtKU8piqW"
];
function bondingCurveMarketCap({
  mintSupply,
  virtualQuoteReserves,
  virtualTokenReserves
}) {
  if (virtualTokenReserves.isZero()) {
    throw new Error("Division by zero: virtual token reserves cannot be zero");
  }
  return virtualQuoteReserves.mul(mintSupply).div(virtualTokenReserves);
}

// src/state.ts
var Platform = /* @__PURE__ */ ((Platform2) => {
  Platform2[Platform2["Pump"] = 0] = "Pump";
  Platform2[Platform2["X"] = 1] = "X";
  Platform2[Platform2["GitHub"] = 2] = "GitHub";
  return Platform2;
})(Platform || {});
var stringToPlatform = (value) => {
  const normalized = value.trim().toUpperCase();
  const entry = Object.entries(Platform).find(
    ([key, val]) => typeof val === "number" && key.toUpperCase() === normalized
  );
  if (entry) {
    return entry[1];
  }
  const validNames = Object.entries(Platform).filter(([, val]) => typeof val === "number").map(([key]) => key.toUpperCase()).join(", ");
  throw new Error(
    `Unknown platform "${value}". Expected one of: ${validNames}`
  );
};
var platformToString = (platform) => {
  const name = Platform[platform];
  if (name !== void 0) {
    return name;
  }
  throw new Error(`Unknown platform value: ${platform}`);
};
