import { TestBed } from '@angular/core/testing';

import { FinanceAPIService } from './finance-api.service';

describe('FinanceAPIService', () => {
  let service: FinanceAPIService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(FinanceAPIService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
